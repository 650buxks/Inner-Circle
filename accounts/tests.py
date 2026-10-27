import io
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

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


def request_reset_link(client, email):
    """Fill in the "forgot password" form and return the reset link sent."""
    client.post(reverse("accounts:password_reset"), {"email": email})
    body = mail.outbox[-1].body
    return re.search(r"https?://\S+", body).group()


def test_forgot_password_page_loads(client):
    response = client.get(reverse("accounts:password_reset"))

    assert response.status_code == 200
    assert "Forgot your password?" in response.content.decode()


def test_login_page_links_to_forgot_password(client):
    response = client.get(reverse("accounts:login"))

    assert reverse("accounts:password_reset") in response.content.decode()


def test_reset_sends_email_with_link(client, francis):
    response = client.post(
        reverse("accounts:password_reset"),
        {"email": "FRANCIS@example.com"},
    )

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["francis@example.com"]
    assert mail.outbox[0].subject == "Reset your Clique password"


def test_reset_for_unknown_email_sends_nothing(client, db):
    response = client.post(
        reverse("accounts:password_reset"),
        {"email": "nobody@example.com"},
    )

    # Same "check your email" page, so nobody can use this form to find
    # out which emails have accounts.
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 0


def test_reset_link_sets_new_password(client, francis):
    link = request_reset_link(client, "francis@example.com")

    # Opening the link redirects to a page that holds the token safely.
    response = client.get(link, follow=True)
    form_url = response.redirect_chain[-1][0]
    response = client.post(
        form_url,
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_complete")
    francis.refresh_from_db()
    assert francis.check_password(NEW_PASSWORD)


def test_reset_link_only_works_once(client, francis):
    link = request_reset_link(client, "francis@example.com")
    response = client.get(link, follow=True)
    form_url = response.redirect_chain[-1][0]
    client.post(
        form_url,
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )

    response = client.get(link, follow=True)

    assert "This link doesn't work" in response.content.decode()


# --- Profile photos ----------------------------------------------------------


@pytest.fixture
def media(settings, tmp_path):
    """Save uploaded photos in a temporary folder that's deleted after."""
    settings.MEDIA_ROOT = tmp_path
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
    }
    return tmp_path


def make_photo(name="me.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "purple").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


def save_profile(client, **changes):
    """Post the Edit profile form, keeping francis's other details."""
    data = {"display_name": "", "username": "francis", "status_message": ""}
    data.update(changes)
    return client.post(reverse("accounts:edit_profile"), data)


def test_upload_profile_photo(media, client, francis):
    client.force_login(francis)

    save_profile(client, avatar=make_photo())

    francis.refresh_from_db()
    assert francis.avatar.name.startswith(f"avatars/{francis.pk}/")
    assert (media / francis.avatar.name).exists()
    page = client.get(reverse("accounts:profile", args=["francis"]))
    assert francis.avatar.url in page.content.decode()


def test_people_without_a_photo_keep_their_letter(client, francis):
    client.force_login(francis)

    page = client.get(reverse("accounts:profile", args=["francis"]))

    assert '<div class="avatar avatar-lg mx-auto mb-3">F</div>' in (page.content.decode())


def test_fake_profile_photo_is_rejected(media, client, francis):
    client.force_login(francis)
    fake = SimpleUploadedFile("me.jpg", b"not a picture")

    response = save_profile(client, avatar=fake)

    assert response.context["form"].errors["avatar"]  # shown on the form
    francis.refresh_from_db()
    assert not francis.avatar


def test_profile_photo_size_limit(media, client, francis, monkeypatch):
    monkeypatch.setattr(User, "MAX_AVATAR_SIZE", 10)  # 10 bytes
    client.force_login(francis)

    response = save_profile(client, avatar=make_photo())

    assert "Photos can be at most" in response.content.decode()


def test_new_photo_replaces_the_old_file(media, client, francis):
    client.force_login(francis)
    save_profile(client, avatar=make_photo())
    francis.refresh_from_db()
    old_file = media / francis.avatar.name

    save_profile(client, avatar=make_photo("new.png"))

    assert not old_file.exists()


def test_remove_profile_photo(media, client, francis):
    client.force_login(francis)
    save_profile(client, avatar=make_photo())
    francis.refresh_from_db()
    old_file = media / francis.avatar.name

    save_profile(client, **{"avatar-clear": "on"})  # the "Clear" tickbox

    francis.refresh_from_db()
    assert not francis.avatar
    assert not old_file.exists()


def test_deleting_account_deletes_profile_photo(media, client, francis):
    client.force_login(francis)
    save_profile(client, avatar=make_photo())
    francis.refresh_from_db()
    photo_file = media / francis.avatar.name

    client.post(
        reverse("accounts:delete_account"),
        {"current_password": SIGNUP_PASSWORD},
    )

    assert not User.objects.filter(pk=francis.pk).exists()
    assert not photo_file.exists()
