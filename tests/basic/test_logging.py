import logging
import re

import pytest

from cyto.logging import log_duration


def test_log_duration(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with log_duration():
        pass
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert re.fullmatch(
        r"Code block \(starting at line \d+\) in test_log_duration took "
        r"\d+\.\d{3} seconds",
        record.message,
    )
