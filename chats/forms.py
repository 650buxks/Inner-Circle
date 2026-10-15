from django import forms

from .models import Conversation


class GroupForm(forms.Form):
    """Name a new group and pick friends to add."""

    name = forms.CharField(
        max_length=Conversation._meta.get_field("name").max_length,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    members = forms.ModelMultipleChoiceField(
        queryset=None,  # filled in __init__ with the user's friends
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Pick at least one friend."},
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = user.friends.order_by("username")


class AddMembersForm(forms.Form):
    """Pick friends who aren't in the group yet."""

    members = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Pick at least one friend."},
    )

    def __init__(self, *args, user, conversation, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = user.friends.exclude(
            conversations=conversation,
        ).order_by("username")
