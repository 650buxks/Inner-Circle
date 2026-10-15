def friend_requests(request):
    """Make the number of waiting friend requests available on every page,
    for the badge in the navbar."""
    if not request.user.is_authenticated:
        return {}
    count = request.user.received_friend_requests.count()
    return {"friend_request_count": count}
