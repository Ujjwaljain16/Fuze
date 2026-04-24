from typing import Dict, Any, Optional
from models import Project
from uow.unit_of_work import UnitOfWork
from core.events import ProjectCreated, ProjectUpdated, ProjectDeleted
from core.logging_config import get_logger

logger = get_logger(__name__)

class ProjectService:
    """
    Orchestrates the lifecycle of Project aggregates.
    Services now strictly record facts (Events); side effects are handled reactively.
    """
    
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create_project(self, user_id: int, title: str, description: str, technologies: str = '') -> Project:
        """Creates a new project and records the fact."""
        project = Project(
            user_id=user_id,
            title=title.strip(),
            description=description.strip(),
            technologies=technologies.strip()
        )
        
        with self.uow as u:
            u.projects.add(project)
            u.session.flush()  # Ensure ID is generated for the event
            # Emit the domain event
            u.emit(ProjectCreated(
                project_id=project.id,
                user_id=user_id,
                title=project.title,
                description=project.description,
                technologies=project.technologies
            ))
        
        return project

    def update_project(self, project_id: int, user_id: int, data: Dict[str, Any]) -> Optional[Project]:
        """Updates project metadata and records the change."""
        with self.uow as u:
            project = u.projects.get_by_id(project_id, user_id)
            if not project:
                return None
            
            # Track changes for fine-grained events (Phase 3 optimization)
            title = data.get('title', project.title).strip()
            desc = data.get('description', project.description).strip()
            tech = data.get('technologies', project.technologies).strip()
            
            title_changed = (title != project.title)
            desc_changed = (desc != project.description)
            tech_changed = (tech != project.technologies)

            project.title = title
            project.description = desc
            project.technologies = tech
            
            # Emit update event ONLY if something changed
            if title_changed or desc_changed or tech_changed:
                u.emit(ProjectUpdated(
                    project_id=project_id,
                    user_id=user_id,
                    title_changed=title_changed,
                    description_changed=desc_changed,
                    technologies_changed=tech_changed
                ))
            
        return project

    def delete_project(self, project_id: int, user_id: int) -> bool:
        """Deletes a project and records the fact."""
        with self.uow as u:
            project = u.projects.get_by_id(project_id, user_id)
            if not project:
                return False
            
            u.projects.delete(project)
            u.emit(ProjectDeleted(project_id=project_id, user_id=user_id))
            
        return True
