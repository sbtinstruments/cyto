import logging

import pytest

from cyto.logging import log_duration


def test_log_duration(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with log_duration():
        pass
    # Note that `record.msg` is the unexpanded log message (in contrast to
    # `record.message`).
    messages = [record.msg for record in caplog.records]
    assert messages == [
        "Code block (starting at line 9) in test_log_duration took %.3f seconds"
    ]
