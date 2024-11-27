from pydantic import Field

from ...factory import FACTORY
from ...model import FrozenModel


class ProjectDatabaseToTrailConfig(FrozenModel):
    only_include: frozenset[str] | None = None
    name_map: dict[str, str] = Field(default_factory=dict)

    def rename(self, project_name: str) -> str:
        """Return the setting-specific name (if any) for the given project."""
        return self.name_map.get(project_name, project_name)


FACTORY.register_product(
    source="default",
    annotation=ProjectDatabaseToTrailConfig,
    factory=lambda _: ProjectDatabaseToTrailConfig(),
)
