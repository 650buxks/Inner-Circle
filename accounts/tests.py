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


@pytest.fixture
def francis(db):
    """A saved user that the login tests can log in as."""
    return User.objects.create_user(
        username="francis",
        email="francis@example.com",
        password=SIGNUP_PASSWORD,
    )


def logged_in_user_id(client):
    """The id of whoever the test browser is logged in as, or None."""
    return client.session.get("_auth_user_id")


def test_login_with_username(client, francis):
    response = client.post(
        reverse("accounts:login"),
        {"username": "francis", "password": SIGNUP_PASSWORD},
    )

    assert response.status_code == 302
    assert logged_in_user_id(client) == str(francis.pk)


def test_login_with_email_ignores_case(client, francis):
    client.post(
        reverse("accounts:login"),
        {"username": "FRANCIS@example.com", "password": SIGNUP_PASSWORD},
    )

    assert logged_in_user_id(client) == str(francis.pk)


def test_login_with_wrong_password_shows_error(client, francis):
    response = client.post(
        reverse("accounts:login"),
        {"username": "francis", "password": "wrong-password"},
    )

    assert response.status_code == 200  # form shown again
    assert "Please enter a correct" in response.content.decode()
    assert logged_in_user_id(client) is None


def test_login_without_remember_me_ends_at_browser_close(client, francis):
    client.post(
        reverse("accounts:login"),
        {"username": "francis", "password": SIGNUP_PASSWORD},
    )

    assert client.session.get_expire_at_browser_close()


def test_login_with_remember_me_keeps_session(client, francis):
    client.post(
        reverse("accounts:login"),
        {
            "username": "francis",
            "password": SIGNUP_PASSWORD,
            "remember_me": "on",
        },
    )

    assert not client.session.get_expire_at_browser_close()


def test_logout(client, francis):
    client.force_login(francis)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert logged_in_user_id(client) is None


def test_profile_requires_login(client, francis):
    url = reverse("accounts:profile", args=["francis"])

    response = client.get(url)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_profile_shows_person_details(client, francis):
    francis.display_name = "Francis Isip"
    francis.status_message = "At the cafe"
    francis.bio = "From the Bay Area."
    francis.save()
    client.force_login(francis)

    response = client.get(reverse("accounts:profile", args=["francis"]))

    page = response.content.decode()
    assert "Francis Isip" in page
    assert "@francis" in page
    assert "At the cafe" in page
    assert "From the Bay Area." in page
    assert "Edit profile" in page  # it's your own profile


def test_other_persons_profile_has_no_edit_button(client, francis):
    User.objects.create_user(username="jordan", password=SIGNUP_PASSWORD)
    client.force_login(francis)

    response = client.get(reverse("accounts:profile", args=["jordan"]))

    assert response.status_code == 200
    assert "Edit profile" not in response.content.decode()


def test_profile_of_unknown_user_is_404(client, francis):
    client.force_login(francis)

    response = client.get(reverse("accounts:profile", args=["nobody"]))

    assert response.status_code == 404


def test_edit_profile_saves_changes(client, francis):
    client.force_login(francis)

    response = client.post(
        reverse("accounts:edit_profile"),
        {
            "display_name": "Francis Isip",
            "username": "francis",
            "status_message": "Coding Clique",
            "bio": "Hi!",
        },
    )

    assert response.status_code == 302
    francis.refresh_from_db()
    assert francis.display_name == "Francis Isip"
    assert francis.status_message == "Coding Clique"
    assert francis.bio == "Hi!"


def test_edit_profile_rejects_taken_username(client, francis):
    User.objects.create_user(username="jordan", password=SIGNUP_PASSWORD)
    client.force_login(francis)

    response = client.post(
        reverse("accounts:edit_profile"),
        {
            "display_name": "",
            "username": "jordan",
            "status_message": "",
            "bio": "",
        },
    )

    assert response.status_code == 200  # form shown again with an error
    assert "already exists" in response.content.decode()
    francis.refresh_from_db()
    assert francis.username == "francis"


NEW_PASSWORD = "brand-new-pass-456"


@pytest.fixture
def logged_in(client, francis):
    """A test browser that's already logged in as francis."""
    client.force_login(francis)
    return client


def test_settings_requires_login(client):
    response = client.get(reverse("accounts:settings"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_settings_page_loads(logged_in):
    response = logged_in.get(reverse("accounts:settings"))

    page = response.content.decode()
    assert response.status_code == 200
    assert "francis@example.com" in page
    assert "Delete my account" in page


def test_change_email(logged_in, francis):
    response = logged_in.post(
        reverse("accounts:change_email"),
        {"email": "new@example.com", "current_password": SIGNUP_PASSWORD},
    )

    assert response.status_code == 302
    francis.refresh_from_db()
    assert francis.email == "new@example.com"


def test_change_email_needs_correct_password(logged_in, francis):
    response = logged_in.post(
        reverse("accounts:change_email"),
        {"email": "new@example.com", "current_password": "wrong"},
    )

    assert "Your password is incorrect." in response.content.decode()
    francis.refresh_from_db()
    assert francis.email == "francis@example.com"


def test_change_email_rejects_taken_email(logged_in, francis):
    User.objects.create_user(
        username="jordan",
        email="jordan@example.com",
        password=SIGNUP_PASSWORD,
    )

    response = logged_in.post(
        reverse("accounts:change_email"),
        {"email": "JORDAN@example.com", "current_password": SIGNUP_PASSWORD},
    )

    error = "An account with this email already exists."
    assert error in response.content.decode()


def test_change_password_keeps_you_logged_in(logged_in, francis):
    response = logged_in.post(
        reverse("accounts:change_password"),
        {
            "old_password": SIGNUP_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )

    assert response.status_code == 302
    francis.refresh_from_db()
    assert francis.check_password(NEW_PASSWORD)
    assert logged_in_user_id(logged_in) == str(francis.pk)


def test_change_password_rejects_wrong_old_password(logged_in, francis):
    logged_in.post(
        reverse("accounts:change_password"),
        {
            "old_password": "wrong",
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )

    francis.refresh_from_db()
    assert francis.check_password(SIGNUP_PASSWORD)


def test_update_ai_settings(logged_in, francis):
    # Unticked checkboxes aren't sent at all, so this turns smart replies
    # off and opts out of AI summaries.
    logged_in.post(reverse("accounts:ai_settings"), {"ai_opt_out": "on"})

    francis.refresh_from_db()
    assert francis.ai_opt_out is True
    assert francis.smart_replies_on is False


def test_delete_account_needs_correct_password(logged_in, francis):
    logged_in.post(
        reverse("accounts:delete_account"),
        {"current_password": "wrong"},
    )

    assert User.objects.filter(pk=francis.pk).exists()


def test_delete_account(logged_in, francis):
    response = logged_in.post(
        reverse("accounts:delete_account"),
        {"current_password": SIGNUP_PASSWORD},
    )

    assert response.status_code == 302
    assert not User.objects.filter(pk=francis.pk).exists()
    assert logged_in_user_id(logged_in) is None


def test_settings_actions_only_accept_post(logged_in):
    response = logged_in.get(reverse("accounts:delete_account"))

    assert response.status_code == 405  # "method not allowed"
