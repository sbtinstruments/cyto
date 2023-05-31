from ...factory import FACTORY
from ...model import FrozenModel


class ProjectDatabaseToTrailConfig(FrozenModel):
    only_include: frozenset[str] | None = None


FACTORY.register_product(
    source="default",
    annotation=ProjectDatabaseToTrailConfig,
    factory=lambda _: ProjectDatabaseToTrailConfig(),
)
