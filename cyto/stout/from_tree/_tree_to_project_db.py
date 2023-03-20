import logging

import anyio

from ...cytio.tree import InstanceMapping, TaskTree
from ...cytio.tree.section import Section
from .._project_database import Project, ProjectDatabase

_LOGGER = logging.getLogger(__name__)


def add_sections_to_db(
    db: ProjectDatabase,
    section: Section,
    *,
    task_id: int,
    task_name: str | None,
    parent: int | None = None,
) -> None:
    # Every project must have a name
    if section.name is None:
        raise ValueError("Section must have a name (or you must provide one for it)")
    # Add the section itself
    project = Project(
        project_name=section.name,
        assignee_id=task_id,
        assignee_name=task_name,
        actual=section.actual,
        planned=section.planned,
        hints=section.hints,
        parent=parent,
    )
    project_id = db.add_project(project)
    # Add all child sections
    for child_section in section.children:
        add_sections_to_db(
            db, child_section, task_id=task_id, task_name=task_name, parent=project_id
        )


def tree_to_project_database(
    tree: TaskTree,
    *,
    db: ProjectDatabase | None = None,
    node: anyio.TaskInfo | None = None,
) -> ProjectDatabase:
    if db is None:
        db = ProjectDatabase()
    if node is None:
        node = tree.root
    for neighbour in tree.graph[node]:
        tree_to_project_database(tree, db=db, node=neighbour)
    try:
        section = InstanceMapping(tree.nodes()[node])[Section]
    except KeyError:
        pass
    else:
        add_sections_to_db(db, section, task_id=node.id, task_name=node.name)
    return db
