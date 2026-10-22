import cloudinary
import cloudinary.uploader
import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse

from core.storage import CloudinaryStorage
from core.tasks import ping


@pytest.mark.django_db
def test_landing_page_loads(client):
    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    page = response.content.decode()
    assert "Your people, your chats" in page
    assert reverse("accounts:signup") in page


@pytest.mark.django_db
def test_health_reports_database_ok(client):
    response = client.get(reverse("core:health"))

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["photos"] == "local"  # no Cloudinary in tests


def test_celery_task_runs():
    # .apply() runs the task right here instead of sending it to a worker.
    assert ping.apply().get() == "pong"


@pytest.mark.django_db
def test_custom_user_model_is_used():
    user = get_user_model().objects.create_user(username="francis", password="s3cure-pass!")

    assert user._meta.label == "accounts.User"
    assert user.check_password("s3cure-pass!")


def test_cloudinary_storage(monkeypatch):
    """Checks our storage class talks to Cloudinary correctly, without
    really uploading anything (the upload and delete calls are faked)."""
    calls = []

    def fake_upload(content, **options):
        calls.append(("upload", options))
        return {"public_id": options["public_id"], "format": "jpg"}

    def fake_destroy(public_id, **options):
        calls.append(("destroy", public_id))

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    monkeypatch.setattr(cloudinary.uploader, "destroy", fake_destroy)
    monkeypatch.setattr(cloudinary.config(), "cloud_name", "demo")
    storage = CloudinaryStorage()

    name = storage.save("chats/1/abc.jpg", ContentFile(b"photo"))
    url = storage.url(name)
    storage.delete(name)

    assert name == "chats/1/abc.jpg"
    assert calls[0] == (
        "upload",
        {"public_id": "chats/1/abc", "resource_type": "image"},
    )
    assert url.startswith("https://res.cloudinary.com/demo/image/upload/")
    assert url.endswith("/chats/1/abc")
    assert calls[1] == ("destroy", "chats/1/abc")
