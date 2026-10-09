import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.tasks import ping


@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    assert "Clique is running" in response.content.decode()


@pytest.mark.django_db
def test_health_reports_database_ok(client):
    response = client.get(reverse("core:health"))

    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_celery_task_runs():
    # .apply() runs the task right here instead of sending it to a worker.
    assert ping.apply().get() == "pong"


@pytest.mark.django_db
def test_custom_user_model_is_used():
    user = get_user_model().objects.create_user(username="francis", password="s3cure-pass!")

    assert user._meta.label == "accounts.User"
    assert user.check_password("s3cure-pass!")
