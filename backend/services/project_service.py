from typing import Dict, Any, Optional
from models import Project
from uow.unit_of_work import UnitOfWork
from core.events import ProjectCreated, ProjectUpdated, ProjectDeleted

class ProjectService:
    """
    Orchestrates the persistence of Project aggregates and emits domain events.
    """
    
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create_project(self, user_id: int, title: str, description: str, technologies: str = '') -> Project:
        """Creates a new project and emits ProjectCreated domain event."""
        project = Project(
            user_id=user_id,
            title=title.strip(),
            description=description.strip(),
            technologies=technologies.strip()
        )
        self.uow.projects.add(project)
        self.uow.flush()

        self.uow.emit(ProjectCreated(
            project_id=project.id,
            user_id=user_id,
            title=project.title,
            description=project.description,
            technologies=project.technologies
        ))
        return project

    def update_project(self, project_id: int, user_id: int, data: Dict[str, Any]) -> Optional[Project]:
        """Updates project metadata and emits ProjectUpdated domain event."""
        project = self.uow.projects.get_by_id(project_id, user_id)
        if not project:
            return None
        
        old_title = project.title
        old_desc = project.description
        old_tech = project.technologies

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
        self.uow.flush()

        self.uow.emit(ProjectUpdated(
            project_id=project.id,
            user_id=user_id,
            title=project.title,
            description=project.description,
            technologies=project.technologies,
            title_changed=(project.title != old_title),
            description_changed=(project.description != old_desc),
            technologies_changed=(project.technologies != old_tech)
        ))
        return project

    def delete_project(self, project_id: int, user_id: int) -> bool:
        """Deletes a project and emits ProjectDeleted domain event."""
        project = self.uow.projects.get_by_id(project_id, user_id)
        if not project:
            return False
        
        self.uow.projects.delete(project)
        self.uow.emit(ProjectDeleted(
            project_id=project_id,
            user_id=user_id
        ))
        return True
