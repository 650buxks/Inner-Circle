"""{% poll_results message.poll user as results %} for drawing a poll."""

from django import template

from chats import services

register = template.Library()


@register.simple_tag
def poll_results(poll, user):
    return services.poll_results(poll, user)
