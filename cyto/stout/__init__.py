"""STOUT (STructured OUTput) is a structured stream that "tracks" an execution."""
try:
    from ._message import Message, MessageSeverity
    from ._outcome import Outcome
    from ._outline import Outline
    from ._project_database import ProjectDatabase, ProjectDatabaseToTrailConfig
    from ._stout import (
        OutcomeSwig,
        OutlineSwig,
        Status,
        StatusSwig,
        Swig,
        is_status_current,
    )
    from ._trail import Trail, TrailSection

except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
