from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import (
    AISettingsForm,
    ChangeEmailForm,
    ChangePasswordForm,
    DeleteAccountForm,
    LoginForm,
    NewPasswordForm,
    ProfileForm,
    ResetRequestForm,
    SignUpForm,
)
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


def settings_page(request, **forms):
    """Show the settings page. Any form passed in (with its errors) replaces
    the empty version of that form."""
    user = request.user
    context = {
        "email_form": ChangeEmailForm(user=user),
        "password_form": ChangePasswordForm(user),
        "ai_form": AISettingsForm(instance=user),
        "delete_form": DeleteAccountForm(user=user),
    }
    context.update(forms)
    return render(request, "accounts/settings.html", context)


@login_required
def account_settings(request):
    return settings_page(request)


@login_required
@require_POST
def change_email(request):
    form = ChangeEmailForm(request.POST, user=request.user)
    if form.is_valid():
        request.user.email = form.cleaned_data["email"]
        request.user.save(update_fields=["email"])
        messages.success(request, "Your email has been updated.")
        return redirect("accounts:settings")
    return settings_page(request, email_form=form)


@login_required
@require_POST
def change_password(request):
    form = ChangePasswordForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        # Changing the password logs out every session, including this
        # one. This keeps you logged in here.
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("accounts:settings")
    return settings_page(request, password_form=form)


@login_required
@require_POST
def update_ai_settings(request):
    form = AISettingsForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Your AI settings have been saved.")
    return redirect("accounts:settings")


@login_required
@require_POST
def delete_account(request):
    form = DeleteAccountForm(request.POST, user=request.user)
    if form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect("core:home")
    return settings_page(request, delete_form=form)


# --- Forgot password ----------------------------------------------------
# Django has a view for each of the four steps. We only choose our own
# templates and forms, and point each step at the next one.


class ResetRequestView(PasswordResetView):
    """Step 1: type your email and we send you a reset link."""

    template_name = "accounts/password_reset.html"
    form_class = ResetRequestForm
    email_template_name = "accounts/emails/password_reset.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class ResetSentView(PasswordResetDoneView):
    """Step 2: "Check your email"."""

    template_name = "accounts/password_reset_done.html"


class ResetConfirmView(PasswordResetConfirmView):
    """Step 3: the link from the email opens this page to pick a password."""

    template_name = "accounts/password_reset_confirm.html"
    form_class = NewPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class ResetCompleteView(PasswordResetCompleteView):
    """Step 4: "Your password has been changed"."""

    template_name = "accounts/password_reset_complete.html"
