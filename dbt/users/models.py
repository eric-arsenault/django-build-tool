from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, ImageField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    avatar = ImageField(upload_to="avatars/", null=True, blank=True)
    first_name = CharField(blank=True, max_length=150, verbose_name="first name")
    last_name = CharField(blank=True, max_length=150, verbose_name="last name")

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": f"{self.first_name} {self.last_name}"})

