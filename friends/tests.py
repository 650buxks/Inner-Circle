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
    mutual_friends,
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


# --- Friend request buttons and Requests page ---------------------------


def press(client, url_name, username, next_url="/"):
    """Press one of the friend buttons (they're all small POST forms)."""
    url = reverse(f"friends:{url_name}", args=[username])
    return client.post(url, {"next": next_url})


def test_add_friend_button_sends_request(logged_in, francis, jordan):
    response = press(logged_in, "send_request", "jordan")

    assert response.status_code == 302
    assert relationship(francis, jordan) == "request_sent"


def test_add_yourself_shows_error_message(logged_in):
    response = press(logged_in, "send_request", "francis")

    assert response.status_code == 302
    assert FriendRequest.objects.count() == 0


def test_accept_button(logged_in, francis, jordan):
    send_friend_request(jordan, francis)

    press(logged_in, "accept", "jordan")

    assert are_friends(francis, jordan)


def test_decline_button(logged_in, francis, jordan):
    send_friend_request(jordan, francis)

    press(logged_in, "decline", "jordan")

    assert relationship(francis, jordan) == "none"


def test_cancel_button(logged_in, francis, jordan):
    send_friend_request(francis, jordan)

    press(logged_in, "cancel", "jordan")

    assert relationship(francis, jordan) == "none"


def test_cannot_accept_a_request_sent_to_someone_else(logged_in, jordan):
    sam = User.objects.create_user(username="sam", password="pass")
    send_friend_request(jordan, sam)

    # Francis tries to accept Jordan's request to Sam.
    response = press(logged_in, "accept", "jordan")

    assert response.status_code == 404
    assert not are_friends(jordan, sam)


def test_buttons_only_accept_post(logged_in, jordan):
    url = reverse("friends:send_request", args=["jordan"])

    response = logged_in.get(url)

    assert response.status_code == 405


def test_buttons_redirect_back_to_safe_pages_only(logged_in, jordan):
    response = press(
        logged_in,
        "send_request",
        "jordan",
        next_url="https://evil.example.com/",
    )

    assert response.url == reverse("friends:requests")


def test_requests_page_lists_received_and_sent(logged_in, francis, jordan):
    sam = User.objects.create_user(username="sam", password="pass")
    send_friend_request(jordan, francis)
    send_friend_request(francis, sam)

    response = logged_in.get(reverse("friends:requests"))

    page = response.content.decode()
    assert "@jordan" in page
    assert "@sam" in page
    assert "Accept" in page
    assert "Cancel request" in page


def test_navbar_shows_request_count(logged_in, francis, jordan):
    send_friend_request(jordan, francis)

    response = logged_in.get(reverse("core:home"))

    assert response.context["friend_request_count"] == 1


def test_profile_shows_add_friend_button(logged_in, jordan):
    url = reverse("accounts:profile", args=["jordan"])

    response = logged_in.get(url)

    assert "Add friend" in response.content.decode()


def test_profile_shows_accept_button(logged_in, francis, jordan):
    send_friend_request(jordan, francis)
    url = reverse("accounts:profile", args=["jordan"])

    response = logged_in.get(url)

    assert "Accept" in response.content.decode()


# --- Friends list, remove friend, mutual friends, private profiles ------


def test_friends_page_lists_your_friends(logged_in, francis, jordan):
    francis.friends.add(jordan)

    response = logged_in.get(reverse("friends:list"))

    assert "@jordan" in response.content.decode()


def test_friends_page_when_you_have_none(logged_in):
    response = logged_in.get(reverse("friends:list"))

    assert "No friends yet" in response.content.decode()


def test_remove_friend_button(logged_in, francis, jordan):
    francis.friends.add(jordan)

    response = press(logged_in, "remove", "jordan")

    assert response.status_code == 302
    assert not are_friends(francis, jordan)


def test_mutual_friends(francis, jordan):
    sam = User.objects.create_user(username="sam", password="pass")
    alex = User.objects.create_user(username="alex", password="pass")
    francis.friends.add(sam, alex)
    jordan.friends.add(sam)

    assert list(mutual_friends(francis, jordan)) == [sam]


def test_profile_shows_mutual_friends(logged_in, francis, jordan):
    sam = User.objects.create_user(username="sam", password="pass")
    francis.friends.add(sam)
    jordan.friends.add(sam)

    response = logged_in.get(reverse("accounts:profile", args=["jordan"]))

    assert "1 mutual friend" in response.content.decode()


def test_non_friends_see_a_limited_profile(logged_in, jordan):
    jordan.bio = "Secret bio"
    jordan.save()

    response = logged_in.get(reverse("accounts:profile", args=["jordan"]))

    page = response.content.decode()
    assert "Secret bio" not in page
    assert "to see their full profile" in page


def test_friends_see_the_full_profile(logged_in, francis, jordan):
    jordan.bio = "Secret bio"
    jordan.save()
    francis.friends.add(jordan)

    response = logged_in.get(reverse("accounts:profile", args=["jordan"]))

    assert "Secret bio" in response.content.decode()
