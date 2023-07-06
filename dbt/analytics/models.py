import os
from django_celery_beat.models import PeriodicTasks
from django.forms import ValidationError
from django.db import models
from django.conf import settings
from django.db.models import (
    Model,
    SET_NULL,
    CASCADE,
    SET_DEFAULT,
    CharField,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKey,
    JSONField,
    OneToOneField,
    BigAutoField,
)
from django_celery_beat.models import PeriodicTask as BasePeriodicTaskModel
from dbt.utils.common import save_profile_yml
from django.db.models.query import QuerySet

PROFILE_NAME_DEV = "DEV"
PROFILE_NAME_PROD = "PROD"
PROFILE_NAME_DEFAULT = PROFILE_NAME_DEV
PROFILE_NAME_CHOICES = [
    (PROFILE_NAME_DEV, "DEV"),
    (PROFILE_NAME_PROD, "PROD"),
]
SSH_KEY_PREFIX = getattr(settings, "SSH_KEY_PREFIX")


class ExtendedQuerySet(QuerySet):
    """Base class for query sets."""

    def update_or_create(self, defaults=None, **kwargs):
        obj, created = self.get_or_create(defaults=defaults, **kwargs)
        if not created:
            self._update_model_with_dict(obj, dict(defaults or {}, **kwargs))
        return obj

    def _update_model_with_dict(self, obj, fields):
        [
            setattr(obj, attr_name, attr_value)
            for attr_name, attr_value in fields.items()
        ]
        obj.save()
        return obj


class ExtendedManager(models.Manager.from_queryset(ExtendedQuerySet)):
    """Manager with common utilities."""


class PeriodicTaskManager(ExtendedManager):
    """Manager for PeriodicTask model."""

    def enabled(self):
        return self.filter(enabled=True)


class PeriodicTask(BasePeriodicTaskModel):
    git_repo = ForeignKey(
        "GitRepo",
        on_delete=SET_NULL,
        related_name="periodic_task_git_repo",
        null=True,
        blank=True,
    )
    profile_yml = ForeignKey(
        "ProfileYAML",
        on_delete=SET_NULL,
        related_name="periodic_task_profile_yml",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        # # replace ' to " in args
        self.args = self.args.replace("'", '"')
        self.kwargs = f'{{"task_id":{self.id}}}'
        super(
            PeriodicTask,
            self,
        ).save(*args, **kwargs)
        PeriodicTasks.update_changed()

    objects = PeriodicTaskManager()
    no_changes = False


class ProfileYAML(Model):
    profile_yml = TextField(max_length=4000)
    name = CharField(
        max_length=255,
        choices=PROFILE_NAME_CHOICES,
        default=PROFILE_NAME_DEFAULT,
        unique=True,
        verbose_name="Profile Name",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        save_profile_yml(self.profile_yml, ".dbt/profiles.yml")
        super(ProfileYAML, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Profile YAML"
        verbose_name_plural = "Profile YAMLs"

    def __str__(self):
        return str(self.name)


class SSHKey(Model):
    name = CharField(max_length=255)

    def __str__(self):
        return self.name

    def public_key(self):
        pub_key_path = os.path.join(
            os.getenv("HOME"), ".ssh/{}{}.pub".format(SSH_KEY_PREFIX, self.id)
        )

        pub_key = ""
        with open(pub_key_path, "r") as pub_key_file:
            pub_key = pub_key_file.readline()
        return pub_key

    class Meta:
        verbose_name = "SSH Key"
        verbose_name_plural = "SSH Keys"


class GitRepo(Model):
    name = CharField(max_length=255, blank=True, null=True)
    url = CharField(help_text="add with personal token", max_length=600)
    ssh_key = OneToOneField(SSHKey, blank=True, null=True, on_delete=CASCADE)

    def public_key(self):
        if self.ssh_key:
            pub_key_path = os.path.join(
                os.getenv("HOME"),
                ".ssh/{}{}.pub".format(SSH_KEY_PREFIX, self.ssh_key.id),
            )

            pub_key = ""
            with open(pub_key_path, "r") as pub_key_file:
                pub_key = pub_key_file.readline()
            return pub_key
        else:
            return "Public key not found"

    def clean(self):
        if self.url.startswith("git"):
            if not self.ssh_key:
                raise ValidationError(
                    "You must choose a ssh key while you are adding repo of ssh key"
                )

        if self.url.startswith("http"):
            if "ghp" not in self.url:
                raise ValidationError("Your git repo must be come with personal token")

    def save(self, *args, **kwargs):
        self.clean()
        super(GitRepo, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Git Repo"
        verbose_name_plural = "Git Repos"

    def __str__(self):
        return self.name


class SubProcessLog(Model):
    details = TextField(max_length=1000)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sub Process Log"
        verbose_name_plural = "SubProcessLogs"


class DBTLogs(Model):
    manifest = JSONField(null=True, blank=True)
    run_results = JSONField(null=True, blank=True)
    sources = JSONField(null=True, blank=True)
    catalog = JSONField(null=True, blank=True)
    command = CharField(max_length=255, null=True, blank=True)
    previous_command = CharField(max_length=255, null=True, blank=True)
    success = BooleanField(default=True)
    fail_reason = TextField(null=True, blank=True, max_length=10000)
    repository_used_name = CharField(max_length=255, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True, blank=True)
    periodic_task_name = CharField(max_length=255, null=True, blank=True)
    profile_yml_used_name = CharField(max_length=255, null=True, blank=True)
    dbt_stdout = TextField(null=True, blank=True, )

    class Meta:
        verbose_name = "DBT Log"
        verbose_name_plural = "DBT Logs"

    def __str__(self):
        return str(self.created_at)


class Args(Model):
    alias = BigAutoField(primary_key=True, unique=True)
    dbt_log = ForeignKey(DBTLogs, on_delete=CASCADE, null=True, blank=True)
    quiet = CharField(max_length=255, null=True, blank=True)
    which = CharField(max_length=255, null=True, blank=True)
    no_print = CharField(max_length=255, null=True, blank=True)
    rpc_method = CharField(max_length=255, null=True, blank=True)
    use_colors = CharField(max_length=255, null=True, blank=True)
    write_json = CharField(max_length=255, null=True, blank=True)
    profiles_dir = CharField(max_length=255, null=True, blank=True)
    partial_parse = CharField(max_length=255, null=True, blank=True)
    printer_width = CharField(max_length=255, null=True, blank=True)
    static_parser = CharField(max_length=255, null=True, blank=True)
    version_check = CharField(max_length=255, null=True, blank=True)
    event_buffer_size = CharField(max_length=255, null=True, blank=True)
    indirect_selection = CharField(max_length=255, null=True, blank=True)
    send_anonymous = CharField(max_length=255, null=True, blank=True)
    usage_stats = CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Arg"
        verbose_name_plural = "Args"

    def __str__(self):
        return str(self.alias)

