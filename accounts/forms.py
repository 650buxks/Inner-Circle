from django import forms
from django.contrib.auth.forms import UserCreationForm

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
            raise forms.ValidationError("""
            An account with this email already exists.""")
        return email
