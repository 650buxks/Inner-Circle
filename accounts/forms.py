from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "display_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Give every input Bootstrap's styling.
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_email(self):
        """Don't allow two accounts with the same email."""
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists.",
            )
        return email


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        label="Remember me",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username or email"
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["password"].widget.attrs["class"] = "form-control"
        self.fields["remember_me"].widget.attrs["class"] = "form-check-input"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "username", "status_message", "bio")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "username": "Letters, numbers and @ . + - _ only.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class StyledFormMixin:
    """Adds Bootstrap classes to every field: checkboxes and text boxes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class PasswordCheckMixin:
    """Asks for the current password before an important change."""

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Your password is incorrect.")
        return password


class ChangeEmailForm(PasswordCheckMixin, StyledFormMixin, forms.Form):
    email = forms.EmailField(label="New email")
    current_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"]
        other_users = User.objects.exclude(pk=self.user.pk)
        if other_users.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists.",
            )
        return email


class ChangePasswordForm(StyledFormMixin, PasswordChangeForm):
    """Django's change-password form, with Bootstrap styling."""


class AISettingsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("smart_replies_on", "ai_opt_out")
        labels = {
            "smart_replies_on": "Show smart reply suggestions",
            "ai_opt_out": "Leave my messages out of AI summaries",
        }
        help_texts = {
            "smart_replies_on": "Quick replies shown above the chat box.",
            "ai_opt_out": "Clique AI won't read your messages when friends "
            "ask it to catch them up.",
        }


class DeleteAccountForm(PasswordCheckMixin, StyledFormMixin, forms.Form):
    current_password = forms.CharField(
        label="Type your password to confirm",
        widget=forms.PasswordInput,
    )
