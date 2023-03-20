from inspect import Parameter

from ...factory import FACTORY
from ...model import FrozenModel


class ProjectDatabaseToTrailConfig(FrozenModel):
    only_include: frozenset[str] | None = None


def _outline_summary_config_factory(param: Parameter) -> ProjectDatabaseToTrailConfig:
    if param.annotation is not ProjectDatabaseToTrailConfig:
        raise ValueError
    return ProjectDatabaseToTrailConfig()


FACTORY.add_factory(_outline_summary_config_factory)
