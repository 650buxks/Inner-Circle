"""The rules for friends, friend requests and blocking.

Views call these functions instead of changing the database themselves, so
the rules live in one place and are easy to test.
"""

from django.db import transaction

from .models import FriendRequest


class FriendshipError(Exception):
    """Raised when an action breaks one of the rules. The message is shown
    to the user."""


def are_friends(user, other):
    return user.friends.filter(pk=other.pk).exists()


def mutual_friends(user, other):
    """People who are friends with both `user` and `other`."""
    return user.friends.filter(pk__in=other.friends.all())


def accepts_requests_from(user, sender):
    """Does `user`'s privacy setting let `sender` send them a request?"""
    if user.friend_requests_from == user.RequestsFrom.FRIENDS_OF_FRIENDS:
        return mutual_friends(user, sender).exists()
    return True


def is_blocked_between(user, other):
    """True if either person has blocked the other."""
    return (
        user.blocked_users.filter(pk=other.pk).exists()
        or other.blocked_users.filter(pk=user.pk).exists()
    )


def relationship(user, other):
    """Describe how `user` is connected to `other`, for buttons on profiles.

    Returns one of: "self", "friends", "request_sent", "request_received",
    "blocked" (you blocked them), "blocked_by" (they blocked you) or "none".
    """
    if user == other:
        return "self"
    if user.blocked_users.filter(pk=other.pk).exists():
        return "blocked"
    if other.blocked_users.filter(pk=user.pk).exists():
        return "blocked_by"
    if are_friends(user, other):
        return "friends"
    if FriendRequest.objects.filter(from_user=user, to_user=other).exists():
        return "request_sent"
    if FriendRequest.objects.filter(from_user=other, to_user=user).exists():
        return "request_received"
    return "none"


@transaction.atomic
def send_friend_request(from_user, to_user):
    """Send a request, or accept theirs if they already asked you.

    Returns the new FriendRequest, or None if you became friends straight
    away.
    """
    if from_user == to_user:
        raise FriendshipError("You can't add yourself as a friend.")
    if is_blocked_between(from_user, to_user):
        raise FriendshipError("You can't send a request to this person.")
    if are_friends(from_user, to_user):
        raise FriendshipError("You're already friends.")

    # They already asked you, so sending one back means "yes".
    their_request = FriendRequest.objects.filter(
        from_user=to_user,
        to_user=from_user,
    ).first()
    if their_request:
        accept_friend_request(their_request)
        return None

    if not accepts_requests_from(to_user, from_user):
        raise FriendshipError(
            f"{to_user.name} only accepts requests from friends of friends.",
        )

    request, created = FriendRequest.objects.get_or_create(
        from_user=from_user,
        to_user=to_user,
    )
    if not created:
        raise FriendshipError("You already sent a friend request.")
    return request


@transaction.atomic
def accept_friend_request(request):
    request.to_user.friends.add(request.from_user)
    request.delete()


def decline_friend_request(request):
    request.delete()


def cancel_friend_request(request):
    request.delete()


def remove_friend(user, other):
    user.friends.remove(other)


@transaction.atomic
def block_user(user, other):
    """Block someone: unfriend them and delete requests both ways."""
    if user == other:
        raise FriendshipError("You can't block yourself.")
    user.friends.remove(other)
    FriendRequest.objects.filter(from_user=user, to_user=other).delete()
    FriendRequest.objects.filter(from_user=other, to_user=user).delete()
    user.blocked_users.add(other)


def unblock_user(user, other):
    user.blocked_users.remove(other)
