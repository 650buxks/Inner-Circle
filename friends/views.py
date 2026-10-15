from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from accounts.models import User

from .services import relationship

MAX_RESULTS = 20


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
