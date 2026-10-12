import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_name_falls_back_to_username():
    user = get_user_model().objects.create_user(username="francis", password="s3cure-pass!")

    assert user.name == "francis"


@pytest.mark.django_db
def test_name_uses_display_name_when_set():
    user = get_user_model().objects.create_user(
        username="francis", password="s3cure-pass!", display_name="Francis Isip"
    )

    assert user.name == "Francis Isip"
