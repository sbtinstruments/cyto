from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, suppress
from types import TracebackType
from typing import Any, Self, TypedDict, cast

from cyto.cytio.broadcast.model import BroadcastModel
from cyto.stout import Outcome

from ._exceptions import OutcomeMessage

_LOGGER = logging.getLogger(__name__)


class MutableOutcome(TypedDict):
    result: Any
    messages: dict[str, Any]


OutcomeLayerMap = dict[str, Outcome]


class _StopNow(BaseException):
    def __init__(self, message: str) -> None:
        super().__init__(f"Stop now due to: {message}")


class OutcomeBuilder(BroadcastModel[Outcome]):
    default_layer_name = "__default__"

    def __init__(
        self,
        *,
        stop_on_message: bool | None = None,
    ) -> None:
        super().__init__(Outcome())
        if stop_on_message is None:
            stop_on_message = False
        self._stop_on_message = stop_on_message
        self._layers: defaultdict[str, Outcome] = defaultdict(Outcome)
        self._stack: ExitStack | None = None

    def __getitem__(self, layer_name: str) -> Outcome:
        return self._layers[layer_name]

    def __setitem__(self, layer_name: str, layer: Outcome) -> None:
        self._layers[layer_name] = layer
        self._push()

    def update(self, layers: dict[str, Outcome]) -> None:
        self._layers.update(layers)
        self._push()

    def merge_with(self, layers: dict[str, Outcome]) -> None:
        raise NotImplementedError
        # ruff: noqa: ERA001
        # for layer_name, outcome in layers.items():
        #     self._layers[layer_name] = self._layers[layer_name].update(
        #         strategy, **outcome.model_dump()
        #     )
        # self._push()

    # TODO: Use the `override` decorator when we get python 3.12
    @contextmanager
    def mutate(  # type: ignore[override]
        self,
        layer_name: str | None = None,
    ) -> Iterator[MutableOutcome]:
        """Make changes to the outcome at the given layer.

        Automatically publishes the changes when you exit the context manager.
        """
        if layer_name is None:
            layer_name = OutcomeBuilder.default_layer_name
        layer = self._layers[layer_name]
        mutable_layer = layer.model_dump()
        try:
            yield cast(MutableOutcome, mutable_layer)
        finally:
            self[layer_name] = Outcome.model_validate(mutable_layer)

    @contextmanager
    def catch_message(self) -> Iterator[None]:
        """Catch `OutcomeMessage` and set it in the `__default__` layer.

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
        self.publish(next_value)
        # Optionally, raise as soon as we get a message
        if self._stop_on_message and next_value.messages:
            _LOGGER.info("Stop now because of message in outcome")
            raise _StopNow("Message in outcome")

    def __enter__(self) -> Self:
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
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        assert self._stack is not None
        return self._stack.__exit__(exc_type, exc_value, traceback)


def _flatten(_layers: dict[str, Outcome]) -> Outcome:
    """Return all the layers merged together into a single result."""
    raise NotImplementedError
    # sorted_layers = (layers[layer_name] for layer_name in sorted(layers))
    # res = Outcome()
    # for layer in sorted_layers:
    #     res = res.update(**layer.model_dump())
    # return res
