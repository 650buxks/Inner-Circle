from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import LoginForm, SignUpForm


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
