from django.urls import path

from . import views

app_name = "friends"

urlpatterns = [
    path("find/", views.find_people, name="find"),
    path("requests/", views.requests_page, name="requests"),
    path("add/<str:username>/", views.send_request, name="send_request"),
    path("accept/<str:username>/", views.accept_request, name="accept"),
    path("decline/<str:username>/", views.decline_request, name="decline"),
    path("cancel/<str:username>/", views.cancel_request, name="cancel"),
]
