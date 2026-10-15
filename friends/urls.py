from django.urls import path

from . import views

app_name = "friends"

urlpatterns = [
    path("find/", views.find_people, name="find"),
]
