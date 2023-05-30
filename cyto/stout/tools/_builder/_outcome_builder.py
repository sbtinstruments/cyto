from __future__ import annotations

import logging
from collections import defaultdict
from contextlib import ExitStack, contextmanager, suppress
from types import TracebackType
from typing import Any, Iterator, Optional, Type, TypedDict

from mergedeep import Strategy

from cyto.cytio.broadcast.model import BroadcastModel
from cyto.stout import Outcome

from ._exceptions import OutcomeMessage

_LOGGER = logging.getLogger(__name__)


MutableKeynote = tuple[dict[str, Any] | str, ...]


class MutableResultMap(TypedDict):
    keynote: MutableKeynote


class MutableOutcome(TypedDict):
    result: MutableResultMap | Any
    messages: dict[str, Any]


OutcomeLayerMap = dict[str, Outcome]


class _StopNow(BaseException):
    pass


class OutcomeBuilder(BroadcastModel[Outcome]):
    def __init__(
        self,
        *,
        stop_on_message: Optional[bool] = None,
    ) -> None:
        super().__init__(Outcome())
        if stop_on_message is None:
            stop_on_message = False
        self._stop_on_message = stop_on_message
        self._layers: defaultdict[str, Outcome] = defaultdict(Outcome)
        self._stack: Optional[ExitStack] = None

    def __getitem__(self, layer_name: str) -> Outcome:
        return self._layers[layer_name]

    def update(self, layers: dict[str, Outcome]) -> None:
        self._layers.update(layers)
        self._push()

    def merge_with(
        self, layers: dict[str, Outcome], *, strategy: Strategy | None = None
    ) -> None:
        for layer_name, outcome in layers.items():
            self._layers[layer_name] = self._layers[layer_name].update(
                strategy, **outcome.dict()
            )
        self._push()

    @contextmanager
    def mutate(self, layer_name: str | None = None) -> Iterator[MutableOutcome]:
        if layer_name is None:
            layer_name = "__default__"
        layer = self._layers[layer_name]
        mutable_layer = layer.dict()
        try:
            yield mutable_layer
        finally:
            self._layers[layer_name] = Outcome.parse_obj(mutable_layer)
            self._push()

    @contextmanager
    def catch_message(self) -> Iterator[None]:
        """Catch `OutcomeMessage` and set it for this outcome.

        Raises `SystemExit` if `stop_on_message` is set.
        """
        try:
            yield
        except OutcomeMessage as exc:
            # Indirectly, this raises `SystemExit` if
            # `_stop_on_message` is True. Effectively, this causes
            # the program to stop now.
            with self.mutate() as outcome:
                outcome["messages"][exc.code] = exc.message

    def _push(self) -> None:
        next_value = _flatten(self._layers)
        # Early out if there is no change
        if next_value == self.latest_value:
            return
        self.set(next_value)
        # Optionally, raise as soon as we get a message
        if self._stop_on_message and next_value.messages:
            _LOGGER.info("Stop now because of message in outcome")
            raise _StopNow("Stop now because of message in outcome")

    def __enter__(self) -> OutcomeBuilder:
        assert self._stack is None
        with ExitStack() as stack:
            super().__enter__()
            stack.push(super().__exit__)
            stack.enter_context(suppress(_StopNow))
            stack.enter_context(self.catch_message())
            self._stack = stack.pop_all()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool | None:
        assert self._stack is not None
        return self._stack.__exit__(exc_type, exc_value, traceback)


def _flatten(layers: dict[str, Outcome]) -> Outcome:
    """Return all the layers merged together into a single result."""
    sorted_layers = (layers[layer_name] for layer_name in sorted(layers))
    res = Outcome()
    for layer in sorted_layers:
        res = res.update(**layer.dict())
    return res
