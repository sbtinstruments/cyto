from logging import LogRecord

from syslog_rfc5424_formatter import RFC5424Formatter as RFC5424FormatterBase

from ...basic import get_app_name


class RFC5424Formatter(RFC5424FormatterBase):  # type: ignore[misc]
    """Log formatter that adheres to RFC5424.

    This is a light wrapper around the excellent `syslog_rfc5424_formatter` library.
    This wrapper uses the logger name as the `MSGID` field. In turn, the global
    application name goes into the `APP-NAME` field.
    """

    def __init__(self, *, app_name: str | None = None):
        super().__init__(sd_id="mysdid")
        if app_name is None:
            app_name = get_app_name()
        self._app_name = app_name

    def format(self, record: LogRecord) -> str:
        """Return the given log record as a formatted string.

        We (cyto team) encourage the use of this pattern:

            logger = logging.getLogger(__name__)

        It automatically adds the module context to the logger instance.
        We place this module context in the MSGID field.
        From RFC5424:

        > The MSGID SHOULD identify the type of message.  For example, a
        > firewall might use the MSGID "TCPIN" for incoming TCP traffic and the
        > MSGID "TCPOUT" for outgoing TCP traffic.  Messages with the same
        > MSGID should reflect events of the same semantics.  The MSGID itself
        > is a string without further semantics.  It is intended for filtering
        > messages on a relay or collector.

        See: https://www.rfc-editor.org/rfc/rfc5424#section-6.2.7
        """
        self._msgid = record.__dict__["name"]
        # We place the global application name in the APP-NAME field.
        # From RFC5424:
        #
        # > The APP-NAME field SHOULD identify the device or application that
        # > originated the message.  It is a string without further semantics.
        # > It is intended for filtering messages on a relay or collector.
        #
        # See: https://www.rfc-editor.org/rfc/rfc5424#section-6.2.5
        record.__dict__["name"] = self._app_name
        return super().format(record)  # type: ignore[no-any-return]
