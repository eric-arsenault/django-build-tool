from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from allauth.utils import set_form_field_order
from django import forms

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class ExtendedSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super(ExtendedSignupForm, self).__init__(*args, **kwargs)
        self.fields["first_name"] = forms.CharField(
            label=_("Fist Name"),
            max_length=255,
            widget=forms.TextInput(
                attrs={"placeholder": _("Fist Name"), "autocomplete": "Fist Name"}
            ),
        )

        self.fields["last_name"] = forms.CharField(
            label=_("Last Name"),
            max_length=255,
            widget=forms.TextInput(
                attrs={"placeholder": _("Last Name"), "autocomplete": "Fist Name"}
            ),
        )

        if hasattr(self, "field_order"):
            set_form_field_order(self, self.field_order)

    field_order = [
        "email",
        'first_name',
        'last_name',
        "password1",
        "password2",  # ignored when not present
    ]
