import logging
from datetime import datetime
from typing import Iterator, Optional

import redis.asyncio as redis

from .....basic import distinct_until_changed
from .._outline import OutlineReceiveStream
from .._outline_summary import OutlineSummary, SummarySegment

_LOGGER = logging.getLogger(__name__)


async def outline_to_redis(receive_stream: OutlineReceiveStream) -> None:
    async with redis.Redis() as client, receive_stream:
        # await client.delete("outline:inactive")
        summary: Optional[OutlineSummary] = None
        async for outline in distinct_until_changed(receive_stream):
            summary = OutlineSummary.from_outline(outline)
            # We recreate (delete and create) the stream because
            # the summary may change completely. A Redis stream is
            # append-only, so recreate is our only means to adapt
            # to these kind of changes.
            # Idiomatically, we should probably not use a Redis stream
            # for this dynamically-changing outline in the first place.
            # In practice, however, it's just much more convenient to plot
            # (e.g., in Grafana) a Redis stream of (time, string) pairs
            # than, say, a Redis key-value where the value is a
            # JSON-representation of the `OutlineSummary`.
            await _push_summary_to_redis(
                client, "outline:active", summary, recreate=True
            )
        if summary is None:
            return
        # This is an "archive" of outlines. When we recreate the
        # "active" outline stream, we delete all the data in said stream.
        # Therefore, we use another ("inactive") stream for archival
        # purposes.
        # Since this is for archival, we limit the summary to "past" segments
        # (and leave out segments planned for the future). This way, the
        # Redis stream IDs won't clash with future outlines.
        await _push_summary_to_redis(
            client, "outline:inactive", summary, filter_to_now=True
        )


async def _push_summary_to_redis(
    client: redis.Redis,
    key: str,
    summary: OutlineSummary,
    *,
    recreate: Optional[bool] = None,
    filter_to_now: Optional[bool] = None,
) -> None:
    if recreate is None:
        recreate = False
    async with client.pipeline() as pipeline:
        if recreate:
            await pipeline.delete(key)
        segment: Optional[SummarySegment] = None
        filtered_segments = _filter_segments(
            summary.segments, filter_to_now=filter_to_now
        )
        for segment in filtered_segments:
            await _push_segment_to_redis(pipeline, key, segment)
        if segment is not None:
            sentinel = SummarySegment(
                name="<Idle>",
                begin_at=segment.end_at,
                end_at=segment.end_at,  # Unused in `_push_segment_to_redis`
            )
            await _push_segment_to_redis(pipeline, key, sentinel)
        await pipeline.execute()


async def _push_segment_to_redis(
    client: redis.Redis, key: str, segment: SummarySegment
) -> None:
    fields = {"name": segment.name}
    timestamp = segment.begin_at.timestamp()
    timestamp_ms = int(timestamp * 1e3)
    # TODO: Use partial IDs (e.g. "1526919030474-*" when we have
    # Redis 7.0 or newer).
    sequence_part = 0
    id_ = f"{timestamp_ms}-{sequence_part}"
    await client.xadd(key, fields, id=id_)


def _filter_segments(
    segments: tuple[SummarySegment, ...],
    *,
    filter_to_now: Optional[bool] = None,
) -> Iterator[SummarySegment]:
    if filter_to_now is None:
        filter_to_now = False
    now = datetime.now()
    for segment in segments:
        if filter_to_now and now < segment.end_at:
            continue
        yield segment
