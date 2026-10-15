from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import User

from .models import FriendRequest
from .services import (
    FriendshipError,
    accept_friend_request,
    cancel_friend_request,
    decline_friend_request,
    relationship,
    remove_friend,
    send_friend_request,
)

MAX_RESULTS = 20


def redirect_back(request):
    """Go back to the page the button was on, or to the Requests page.

    Only addresses on this site are allowed, so nobody can trick Clique
    into sending people to another website.
    """
    next_url = request.POST.get("next", "")
    is_safe = url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    if is_safe:
        return redirect(next_url)
    return redirect("friends:requests")


@login_required
def find_people(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        me = request.user
        by_username = Q(username__icontains=query)
        by_name = Q(display_name__icontains=query)
        results = list(
            User.objects.filter(by_username | by_name, is_active=True)
            .exclude(pk=me.pk)
            # Hide people you've blocked and people who've blocked you.
            .exclude(pk__in=me.blocked_users.all())
            .exclude(pk__in=me.blocked_by.all())
            .order_by("username")[:MAX_RESULTS]
        )
        # Label each person ("Friends", "Request sent"...) for the page.
        for person in results:
            person.relationship = relationship(me, person)

    context = {"query": query, "results": results}
    return render(request, "friends/find.html", context)


@login_required
def friends_list(request):
    friends = request.user.friends.order_by("username")
    return render(request, "friends/list.html", {"friends": friends})


@login_required
def requests_page(request):
    me = request.user
    context = {
        "received": me.received_friend_requests.select_related("from_user"),
        "sent": me.sent_friend_requests.select_related("to_user"),
    }
    return render(request, "friends/requests.html", context)


@login_required
@require_POST
def send_request(request, username):
    person = get_object_or_404(User, username=username, is_active=True)
    try:
        friend_request = send_friend_request(request.user, person)
    except FriendshipError as error:
        messages.error(request, str(error))
    else:
        if friend_request is None:
            text = f"You're now friends with {person.name}!"
        else:
            text = f"Friend request sent to {person.name}."
        messages.success(request, text)
    return redirect_back(request)


@login_required
@require_POST
def accept_request(request, username):
    friend_request = get_object_or_404(
        FriendRequest,
        from_user__username=username,
        to_user=request.user,
    )
    accept_friend_request(friend_request)
    name = friend_request.from_user.name
    messages.success(request, f"You're now friends with {name}!")
    return redirect_back(request)


@login_required
@require_POST
def decline_request(request, username):
    friend_request = get_object_or_404(
        FriendRequest,
        from_user__username=username,
        to_user=request.user,
    )
    decline_friend_request(friend_request)
    messages.info(request, "Friend request declined.")
    return redirect_back(request)


@login_required
@require_POST
def cancel_request(request, username):
    friend_request = get_object_or_404(
        FriendRequest,
        from_user=request.user,
        to_user__username=username,
    )
    cancel_friend_request(friend_request)
    messages.info(request, "Friend request cancelled.")
    return redirect_back(request)


@login_required
@require_POST
def unfriend(request, username):
    person = get_object_or_404(User, username=username)
    remove_friend(request.user, person)
    messages.info(request, f"You and {person.name} are no longer friends.")
    return redirect_back(request)
