import pytest
from models import Project, Task, Subtask, db
from repositories.project_repository import ProjectRepository, MAX_PAGE_SIZE


@pytest.mark.unit
@pytest.mark.requires_db
def test_project_repository_ownership_scoping(test_user, app):
    with app.app_context():
        repo = ProjectRepository(db.session)

        # Create project, task, and subtask for user A
        project = Project(
            user_id=test_user['id'],
            title='User A Project',
            description='Desc'
        )
        repo.add(project)
        db.session.commit()

        task = Task(project_id=project.id, title='User A Task')
        db.session.add(task)
        db.session.commit()

        subtask = Subtask(task_id=task.id, title='User A Subtask')
        db.session.add(subtask)
        db.session.commit()

        # 1. Fetch task by ID without ownership filter
        t_global = repo.get_task_id = repo.get_task_by_id(task.id)
        assert t_global is not None

        # 2. Fetch task by ID with user ownership check
        t_owned = repo.get_task_by_id(task.id, user_id=test_user['id'])
        assert t_owned is not None
        assert t_owned.id == task.id

        # 3. Fetch task by ID with OTHER user ownership check (should return None!)
        t_unowned = repo.get_task_by_id(task.id, user_id=99999)
        assert t_unowned is None

        # 4. Fetch subtask by ID with OTHER user ownership check (should return None!)
        st_unowned = repo.get_subtask_by_id(subtask.id, user_id=99999)
        assert st_unowned is None

        # 5. Fetch project with tasks eagerly loaded
        p_loaded = repo.get_by_id_with_tasks(project.id, test_user['id'])
        assert p_loaded is not None
        assert len(p_loaded.tasks) == 1
        assert len(p_loaded.tasks[0].subtasks) == 1


@pytest.mark.unit
@pytest.mark.requires_db
def test_project_repository_pagination_bounds(test_user, app):
    with app.app_context():
        repo = ProjectRepository(db.session)
        paginated = repo.list_by_user(test_user['id'], page=1, per_page=1000)
        assert paginated.per_page == MAX_PAGE_SIZE
