import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

SIGNUP_PASSWORD = "clique-test-pass-123"


@pytest.mark.django_db
def test_name_falls_back_to_username():
    user = User.objects.create_user(
        username="francis",
        password="s3cure-pass!",
    )

    assert user.name == "francis"


@pytest.mark.django_db
def test_name_uses_display_name_when_set():
    user = User.objects.create_user(
        username="francis",
        password="s3cure-pass!",
        display_name="Francis Isip",
    )

    assert user.name == "Francis Isip"


@pytest.mark.django_db
def test_signup_page_loads(client):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == 200
    assert "Create your account" in response.content.decode()


@pytest.mark.django_db
def test_signup_creates_user_and_logs_them_in(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "jordan",
            "display_name": "Jordan Lee",
            "email": "jordan@example.com",
            "password1": SIGNUP_PASSWORD,
            "password2": SIGNUP_PASSWORD,
        },
    )

    assert response.status_code == 302  # redirected to the home page
    user = User.objects.get(username="jordan")
    assert user.display_name == "Jordan Lee"
    assert client.session["_auth_user_id"] == str(user.pk)  # logged in


@pytest.mark.django_db
def test_signup_rejects_duplicate_email(client):
    User.objects.create_user(
        username="francis",
        email="francis@example.com",
        password="s3cure-pass!",
    )

    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "someone-else",
            "email": "FRANCIS@example.com",
            "password1": SIGNUP_PASSWORD,
            "password2": SIGNUP_PASSWORD,
        },
    )

    error = "An account with this email already exists."
    assert response.status_code == 200  # form shown again, no redirect
    assert error in response.content.decode()
    assert not User.objects.filter(username="someone-else").exists()
