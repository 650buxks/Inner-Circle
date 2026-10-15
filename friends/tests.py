import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

from .models import FriendRequest
from .services import (
    FriendshipError,
    accept_friend_request,
    are_friends,
    block_user,
    relationship,
    remove_friend,
    send_friend_request,
    unblock_user,
)

User = get_user_model()


@pytest.fixture
def francis(db):
    return User.objects.create_user(username="francis", password="pass")


@pytest.fixture
def jordan(db):
    return User.objects.create_user(username="jordan", password="pass")


def test_friendship_goes_both_ways(francis, jordan):
    francis.friends.add(jordan)

    assert jordan in francis.friends.all()
    assert francis in jordan.friends.all()


def test_send_and_accept_friend_request(francis, jordan):
    request = send_friend_request(francis, jordan)
    assert relationship(francis, jordan) == "request_sent"
    assert relationship(jordan, francis) == "request_received"

    accept_friend_request(request)

    assert are_friends(francis, jordan)
    assert relationship(francis, jordan) == "friends"
    assert not FriendRequest.objects.exists()


def test_sending_back_a_request_accepts_it(francis, jordan):
    send_friend_request(francis, jordan)

    result = send_friend_request(jordan, francis)

    assert result is None
    assert are_friends(francis, jordan)


def test_cannot_friend_yourself(francis):
    with pytest.raises(FriendshipError):
        send_friend_request(francis, francis)


def test_cannot_send_request_twice(francis, jordan):
    send_friend_request(francis, jordan)

    with pytest.raises(FriendshipError, match="already sent"):
        send_friend_request(francis, jordan)


def test_cannot_send_request_to_a_friend(francis, jordan):
    francis.friends.add(jordan)

    with pytest.raises(FriendshipError, match="already friends"):
        send_friend_request(francis, jordan)


def test_database_rejects_duplicate_requests(francis, jordan):
    # Even if some code skipped the rules above, the database itself
    # refuses a second identical request.
    FriendRequest.objects.create(from_user=francis, to_user=jordan)

    with pytest.raises(IntegrityError):
        FriendRequest.objects.create(from_user=francis, to_user=jordan)


def test_remove_friend(francis, jordan):
    francis.friends.add(jordan)

    remove_friend(jordan, francis)

    assert not are_friends(francis, jordan)


def test_block_unfriends_and_deletes_requests(francis, jordan):
    francis.friends.add(jordan)
    FriendRequest.objects.create(from_user=jordan, to_user=francis)

    block_user(francis, jordan)

    assert not are_friends(francis, jordan)
    assert not FriendRequest.objects.exists()
    assert relationship(francis, jordan) == "blocked"
    assert relationship(jordan, francis) == "blocked_by"


def test_blocked_people_cannot_send_requests(francis, jordan):
    block_user(francis, jordan)

    with pytest.raises(FriendshipError):
        send_friend_request(jordan, francis)
    with pytest.raises(FriendshipError):
        send_friend_request(francis, jordan)


def test_unblock(francis, jordan):
    block_user(francis, jordan)

    unblock_user(francis, jordan)

    assert relationship(francis, jordan) == "none"


# --- Find people page ---------------------------------------------------


def search(client, query):
    """Search on the Find people page and return the page's HTML."""
    response = client.get(reverse("friends:find"), {"q": query})
    return response.content.decode()


@pytest.fixture
def logged_in(client, francis):
    client.force_login(francis)
    return client


def test_find_people_requires_login(client):
    response = client.get(reverse("friends:find"))

    assert response.status_code == 302


def test_find_people_page_loads_without_a_search(logged_in):
    response = logged_in.get(reverse("friends:find"))

    assert response.status_code == 200
    assert "Search for friends" in response.content.decode()


def test_search_by_username_ignores_case(logged_in, jordan):
    assert "@jordan" in search(logged_in, "JOR")


def test_search_by_display_name(logged_in, jordan):
    jordan.display_name = "Jordan Lee"
    jordan.save()

    assert "@jordan" in search(logged_in, "lee")


def test_search_does_not_show_yourself(logged_in):
    assert "@francis" not in search(logged_in, "francis")


def test_search_shows_no_results_message(logged_in):
    assert 'No one found for "zzz"' in search(logged_in, "zzz")


def test_search_hides_blocked_people(logged_in, francis, jordan):
    block_user(francis, jordan)

    assert "@jordan" not in search(logged_in, "jordan")


def test_search_hides_people_who_blocked_you(logged_in, francis, jordan):
    block_user(jordan, francis)

    assert "@jordan" not in search(logged_in, "jordan")


def test_search_hides_deactivated_accounts(logged_in, jordan):
    jordan.is_active = False
    jordan.save()

    assert "@jordan" not in search(logged_in, "jordan")


def test_search_shows_relationship(logged_in, francis, jordan):
    send_friend_request(francis, jordan)

    assert "Request sent" in search(logged_in, "jordan")
