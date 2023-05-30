from cyto.stout import Message


class OutcomeMessage(BaseException):
    """Raise within an `OutcomeBuilder` context to add a message."""

    def __init__(self, code: str, message: Message) -> None:
        super().__init__()
        self._code = code
        self._message = message

    @property
    def code(self) -> str:
        return self._code

    @property
    def message(self) -> Message:
        return self._message


class OutcomeError(OutcomeMessage):
    """Raise within an `OutcomeBuilder` context to add an error message."""

    def __init__(
        self,
        *,
        code: str,
        tech_cause: str,
        user_cause: str,
        user_consequence: str,
        user_suggestion: str,
    ) -> None:
        message = Message.error(
            tech_cause=tech_cause,
            user_cause=user_cause,
            user_consequence=user_consequence,
            user_suggestion=user_suggestion,
        )
        super().__init__(code, message)
