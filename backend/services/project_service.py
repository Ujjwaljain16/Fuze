from typing import Dict, Any, Optional
from models import Project
from uow.unit_of_work import UnitOfWork

class ProjectService:
    """
    Orchestrates the persistence of Project aggregates.
    Note: Currently handles ONLY persistence. Side effects (ML/Cache) 
    are kept procedural in the routes pending event handler migration.
    """
    
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create_project(self, user_id: int, title: str, description: str, technologies: str = '') -> Project:
        """Creates a new project purely in the persistence layer."""
        project = Project(
            user_id=user_id,
            title=title.strip(),
            description=description.strip(),
            technologies=technologies.strip()
        )
        self.uow.projects.add(project)
        return project

    def update_project(self, project_id: int, user_id: int, data: Dict[str, Any]) -> Optional[Project]:
        """Updates project metadata purely in the persistence layer."""
        project = self.uow.projects.get_by_id(project_id, user_id)
        if not project:
            return None
        
        title = data.get('title')
        description = data.get('description')
        technologies = data.get('technologies')

        if title is not None:
            project.title = title.strip()
        if description is not None:
            project.description = description.strip()
        if technologies is not None:
            project.technologies = technologies.strip()
        
        self.uow.projects.update(project)
        return project

    def delete_project(self, project_id: int, user_id: int) -> bool:
        """Deletes a project purely in the persistence layer."""
        project = self.uow.projects.get_by_id(project_id, user_id)
        if not project:
            return False
        
        self.uow.projects.delete(project)
        return True
