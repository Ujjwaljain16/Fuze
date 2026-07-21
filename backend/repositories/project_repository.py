from typing import List, Optional
from models import Project, Task, Subtask

class ProjectRepository:
    """Core repository for Project aggregate (includes Tasks and Subtasks)"""
    
    def __init__(self, session):
        self.session = session

    def get_by_id(self, project_id: int, user_id: int) -> Optional[Project]:
        """Fetch project by ID and UserID (RLS-like check)"""
        return self.session.query(Project).filter_by(id=project_id, user_id=user_id).first()

    def list_by_user(self, user_id: int, page: int = 1, per_page: int = 10):
        """Paginated list of projects for a user"""
        return Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    def add(self, project: Project):
        """Persist a new project"""
        self.session.add(project)
        return project

    def delete(self, project: Project):
        """Remove a project"""
        self.session.delete(project)

    def get_tasks(self, project_id: int) -> List[Task]:
        """Fetch tasks for a project"""
        return self.session.query(Task).filter_by(project_id=project_id).all()
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        return self.session.query(Task).get(task_id)

    def get_subtask_by_id(self, subtask_id: int) -> Optional[Subtask]:
        return self.session.query(Subtask).get(subtask_id)
