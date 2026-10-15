from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LoginForm, ProfileForm, SignUpForm
from .models import User


def signup(request):
    # Already logged in? There's no reason to sign up again.
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("core:home")
    else:
        form = SignUpForm()

    return render(request, "accounts/signup.html", {"form": form})


class CliqueLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        if not form.cleaned_data["remember_me"]:
            # Log out when the browser closes.
            self.request.session.set_expiry(0)
        return super().form_valid(form)


@login_required
def profile(request, username):
    person = get_object_or_404(User, username=username)
    context = {"person": person, "is_me": person == request.user}
    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile(request):
    # Edit a fresh copy of the user, so a form with errors can't change the
    # name shown in the navbar before anything is saved.
    me = User.objects.get(pk=request.user.pk)

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=me)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile", username=me.username)
    else:
        form = ProfileForm(instance=me)

    return render(request, "accounts/edit_profile.html", {"form": form})
