from uuid import uuid4
import pytest


@pytest.fixture
def projects_manager(db_session):
    from app.database.managers.projects_managers import ProjectsManager
    return ProjectsManager(session=db_session)


@pytest.fixture
def seed_user(db_session):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users
    user = Users(
        user_id=uuid4(),
        login="test_user",
        password_hash="hashed_password",
        name="Test User",
        role='user',
        deleted=False
    )
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


@pytest.fixture
def seed_object(db_session):
    """
    Добавляет тестовый объект в базу перед тестом.
    """
    from app.database.models import Objects
    obj = Objects(
        object_id=uuid4(),
        name="Test Object",
        address="123 Test St",
        description="Test Description",
        status=None,
        deleted=False
    )
    db_session.add(obj)
    db_session.commit()
    return obj.to_dict()


@pytest.fixture
def seed_project(db_session, seed_user, seed_object):
    """
    Добавляет тестовый проект в базу перед тестом.
    """
    from app.database.models import Projects
    project = Projects(
        project_id=uuid4(),
        name="Test Project",
        object=seed_object['object_id'],
        project_leader=seed_user['user_id'],
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


def test_add_project(client, jwt_token, db_session, seed_user, seed_object):
    """
    Тест на добавление нового проекта через API.
    """
    data = {
        "name": "New Project",
        "object": seed_object['object_id'],
        "project_leader": seed_user['user_id']
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/projects/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New project added successfully"

    # Проверяем, что проект добавлен в базу
    from app.database.models import Projects
    project = db_session.query(Projects).filter_by(name="New Project").first()
    assert project is not None
    assert project.name == "New Project"
    assert str(project.object) == seed_object['object_id']
    assert str(project.project_leader) == seed_user['user_id']


def test_view_project(client, jwt_token, seed_project):
    """
    Тест на просмотр данных проекта через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/projects/{str(seed_project['project_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "project" in response.json
    assert response.json["msg"] == "Project found successfully"
    assert response.json["project"]["name"] == seed_project['name']


def test_soft_delete_project(client, jwt_token, seed_project):
    """
    Тест на мягкое удаление проекта.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/projects/{str(seed_project['project_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project {
        seed_project['project_id']} soft deleted successfully"

    # Проверяем, что проект помечен как удаленный
    from app.database.models import Projects
    from app.database.managers.projects_managers import ProjectsManager
    projects_manager = ProjectsManager()
    with projects_manager.session_scope() as session:
        project = session.query(Projects).filter_by(
            project_id=seed_project['project_id']).first()
        assert project.deleted is True


def test_hard_delete_project(client, jwt_token, seed_project, db_session):
    """
    Тест на жесткое удаление проекта.
    """
    from app.database.models import Projects

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/projects/{str(seed_project['project_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project {
        seed_project['project_id']} hard deleted successfully"

    # Проверяем, что проект удален из базы
    project = db_session.query(Projects).filter_by(
        project_id=seed_project['project_id']).first()
    assert project is None


def test_edit_project(client, jwt_token, seed_project):
    """
    Тест на редактирование данных проекта через API.
    """
    data = {
        "name": "Updated Project"
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/projects/{str(seed_project['project_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project edited successfully"

    # Проверяем обновленные данные в базе
    from app.database.models import Projects
    from app.database.managers.projects_managers import ProjectsManager
    projects_manager = ProjectsManager()
    with projects_manager.session_scope() as session:
        project = session.query(Projects).filter_by(
            project_id=seed_project['project_id']).first()
        assert project.name == "Updated Project"


def test_get_all_projects(client, jwt_token, seed_project):
    """
    Тест на получение списка проектов через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/projects/all", headers=headers)

    assert response.status_code == 200
    assert "projects" in response.json
    assert response.json["msg"] == "Projects found successfully"

    # Проверяем, что тестовый проект присутствует в списке
    projects = response.json["projects"]
    assert any(p["project_id"] == str(seed_project['project_id'])
               for p in projects)