from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from models import Project, Task, Subtask

MAX_PAGE_SIZE = 100


class ProjectRepository:
    """Core repository for Project aggregate (includes Tasks and Subtasks)"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, project_id: int, user_id: int) -> Optional[Project]:
        """Fetch project by ID and UserID (user ownership boundary check)"""
        return self.session.query(Project).filter_by(id=project_id, user_id=user_id).first()

    def get_by_id_with_tasks(self, project_id: int, user_id: int) -> Optional[Project]:
        """Fetch project by ID eagerly loading tasks and subtasks."""
        return (
            self.session.query(Project)
            .options(selectinload(Project.tasks).selectinload(Task.subtasks))
            .filter_by(id=project_id, user_id=user_id)
            .first()
        )

    def list_by_user(self, user_id: int, page: int = 1, per_page: int = 10, eager_load_tasks: bool = False):
        """Paginated list of projects for a user with optional eager task loading and bounded page size"""
        per_page = max(1, min(per_page, MAX_PAGE_SIZE))
        query = self.session.query(Project).filter_by(user_id=user_id).order_by(Project.created_at.desc())
        if eager_load_tasks:
            query = query.options(selectinload(Project.tasks).selectinload(Task.subtasks))
        return query.paginate(page=page, per_page=per_page, error_out=False)

    def add(self, project: Project) -> Project:
        """Persist a new project"""
        self.session.add(project)
        return project

    def update(self, project: Project) -> Project:
        """Update a project entity"""
        self.session.add(project)
        return project

    def delete(self, project: Project):
        """Remove a project"""
        self.session.delete(project)

    def get_tasks(self, project_id: int) -> List[Task]:
        """Fetch tasks for a project with subtasks eagerly loaded to eliminate N+1 queries"""
        return (
            self.session.query(Task)
            .options(selectinload(Task.subtasks))
            .filter_by(project_id=project_id)
            .order_by(Task.created_at.asc())
            .all()
        )

    def get_task_by_id(self, task_id: int, user_id: Optional[int] = None) -> Optional[Task]:
        """Fetch task by ID using modern session.get() and optional user ownership check"""
        if user_id is not None:
            return (
                self.session.query(Task)
                .join(Project)
                .filter(Task.id == task_id, Project.user_id == user_id)
                .first()
            )
        return self.session.get(Task, task_id)

    def get_subtask_by_id(self, subtask_id: int, user_id: Optional[int] = None) -> Optional[Subtask]:
        """Fetch subtask by ID using modern session.get() and optional user ownership check"""
        if user_id is not None:
            return (
                self.session.query(Subtask)
                .join(Task)
                .join(Project)
                .filter(Subtask.id == subtask_id, Project.user_id == user_id)
                .first()
            )
        return self.session.get(Subtask, subtask_id)
