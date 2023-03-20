from __future__ import annotations

from typing import Any, Literal

from ..model import FrozenModel

MessageSeverity = Literal["error", "warning", "info", "debug"]


class MessageTech(FrozenModel):
    """Technical troubleshooting texts."""

    cause: str


class MessageUser(FrozenModel):
    """User-friendly troubleshooting texts."""

    cause: str
    consequence: str
    suggestion: str


class Message(FrozenModel):
    """A message for troubleshooting."""

    severity: MessageSeverity
    tech: MessageTech
    user: MessageUser

    @classmethod
    def error(
        cls,
        tech_cause: str,
        user_cause: str,
        user_consequence: str,
        user_suggestion: str,
    ) -> Message:
        """Return an "error" Message instance."""
        tech = MessageTech(cause=tech_cause)
        user = MessageUser(
            cause=user_cause, consequence=user_consequence, suggestion=user_suggestion
        )
        return Message(severity="error", tech=tech, user=user)

    @classmethod
    def debug(
        cls,
        tech_cause: str,
        user_cause: str,
        user_consequence: str,
        user_suggestion: str,
    ) -> Message:
        """Return a "debug" Message instance."""
        tech = MessageTech(cause=tech_cause)
        user = MessageUser(
            cause=user_cause, consequence=user_consequence, suggestion=user_suggestion
        )
        return Message(severity="debug", tech=tech, user=user)

    def with_formatting(self, *args: Any, **kwargs: Any) -> Message:
        """Return copy with formatted strings.

        Does not modify this instance. Returns a new Message instance.
        """
        tech_cause = self.tech.cause.format(*args, **kwargs)
        user_cause = self.user.cause.format(*args, **kwargs)
        user_consequence = self.user.consequence.format(*args, **kwargs)
        user_suggestion = self.user.suggestion.format(*args, **kwargs)
        return Message(
            severity=self.severity,
            tech=MessageTech(cause=tech_cause),
            user=MessageUser(
                cause=user_cause,
                consequence=user_consequence,
                suggestion=user_suggestion,
            ),
        )
