from django.urls import path

from . import views

app_name = "chats"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/", views.chat_detail, name="detail"),
    path("<int:pk>/send/", views.send, name="send"),
    path("<int:pk>/media/", views.media, name="media"),
    path("<int:pk>/catch-up/", views.catch_up, name="catch_up"),
    path("start/<str:username>/", views.start_chat, name="start"),
    path("messages/<int:pk>/edit/", views.edit, name="edit"),
    path("messages/<int:pk>/delete/", views.delete, name="delete"),
    # Group chats
    path("groups/new/", views.new_group, name="new_group"),
    path("<int:pk>/settings/", views.group_settings, name="group_settings"),
    path("<int:pk>/rename/", views.rename, name="rename"),
    path("<int:pk>/add/", views.add_people, name="add_members"),
    path(
        "<int:pk>/remove/<str:username>/",
        views.remove,
        name="remove_member",
    ),
    path(
        "<int:pk>/make-admin/<str:username>/",
        views.promote,
        name="make_admin",
    ),
    path("<int:pk>/leave/", views.leave, name="leave"),
]
