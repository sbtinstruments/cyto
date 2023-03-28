import json

import redis.asyncio as redis

from cyto.basic import distinct_until_changed

from .._models import OutcomeReceiveStream, ProgramOutcome


async def outcome_to_redis(receive_stream: OutcomeReceiveStream) -> None:
    async with redis.Redis() as client, receive_stream:
        async for outcome in distinct_until_changed(receive_stream):
            await _push_outcome_to_redis(client, "outcome", outcome)


async def _push_outcome_to_redis(
    client: redis.Redis, key: str, outcome: ProgramOutcome
) -> None:
    if outcome.result is not None:
        outcome_result = outcome.result.json()
    else:
        outcome_result = ""
    outcome_messages = json.dumps(
        [{"code": code, **message.dict()} for code, message in outcome.messages.items()]
    )
    fields = {"result": outcome_result, "messages": outcome_messages}
    await client.xadd(key, fields)
