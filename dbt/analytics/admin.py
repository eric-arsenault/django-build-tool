from django import forms
from django.contrib import admin, messages
from django.forms import ModelForm, PasswordInput
from celery import current_app
from django.contrib.auth.models import Group

from django.contrib.sites.models import Site
from django.forms.widgets import Select
from celery.utils import cached_property
from django_celery_beat.admin import (
    PeriodicTaskAdmin as BasePeriodicTaskAdmin,
    PeriodicTaskForm as BasePeriodicTaskForm,
)

from dbt.analytics.models import (
    DBTLogs,
    GitRepo,
    ProfileYAML,
    SubProcessLog,
    PeriodicTask,
)
from dbt.utils.common import clone_git_repo


class GitRepoForm(ModelForm):
    url = forms.CharField(widget=PasswordInput())

    class Meta:
        model = GitRepo
        fields = "__all__"


@admin.register(DBTLogs)
class DBTLogsLAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "completed_at",
        "success",
        "repository_used_name",
        "command",
        "previous_command",
        "periodic_task_name",
        "profile_yml_used_name",
    ]
    readonly_fields = [
        "repository_used_name",
        "periodic_task_name",
        "profile_yml_used_name",
    ]


@admin.register(ProfileYAML)
class ProfileYAMLAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "profile_yml",
    ]

    def has_add_permission(self, request):
        count = ProfileYAML.objects.all().count()
        if count < 2:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GitRepo)
class GitRepoAdmin(admin.ModelAdmin):
    # form = GitRepoForm
    list_display = [
        "id",
        "name",
        "public_key",
    ]

    def save_model(self, request, obj, form, change):
        obj.save()
        result, msg = clone_git_repo(obj)
        if result:
            ...
        else:
            obj.delete()
            messages.error(request, f"Something is wrong while git cloning {msg}")


@admin.register(SubProcessLog)
class SubprocessAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "details",
    ]


class ProfileSelectWidget(Select):
    """Widget that lets you choose between task names."""

    celery_app = current_app
    _choices = None

    def profiles_as_choices(self):
        _ = self._modules  # noqa
        tasks = list(
            sorted(
                name for name in self.celery_app.tasks if not name.startswith("celery.")
            )
        )
        return (("", ""),) + tuple(zip(tasks, tasks))

    @property
    def choices(self):
        if self._choices is None:
            self._choices = self.profiles_as_choices()
        return self._choices

    @choices.setter
    def choices(self, _):
        pass

    @cached_property
    def _modules(self):
        self.celery_app.loader.import_default_modules()


class ProfileChoiceField(forms.ChoiceField):
    widget = ProfileSelectWidget

    def valid_value(self, value):
        return True


class PeriodicTaskForm(BasePeriodicTaskForm):
    profile_yml = ProfileChoiceField(
        label="Profile YAML",
        required=False,
    )

    class Meta:
        model = PeriodicTask
        exclude = ()


class PeriodicTaskAdmin(BasePeriodicTaskAdmin):
    # form = PeriodicTaskForm
    model = PeriodicTask
    list_display = ('__str__', 'id',  'enabled', 'interval', 'start_time',
                    'last_run_at', 'one_off')
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "git_repo",
                    "profile_yml",
                    "regtask",
                    "task",
                    "enabled",
                    "description",
                ),
                "classes": ("extrapretty", "wide"),
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "interval",
                    "crontab",
                    "solar",
                    "clocked",
                    "start_time",
                    "last_run_at",
                    "one_off",
                ),
                "classes": ("extrapretty", "wide"),
            },
        ),
        (
            "Arguments",
            {
                "fields": ("args",),
                "classes": ("extrapretty", "wide", "collapse", "in"),
            },
        ),
        (
            "Execution Options",
            {
                "fields": (
                    "expires",
                    "expire_seconds",
                    "queue",
                    "exchange",
                    "routing_key",
                    "priority",
                    "headers",
                ),
                "classes": ("extrapretty", "wide", "collapse", "in"),
            },
        ),
    )


#

if PeriodicTask in admin.site._registry:
    admin.site.unregister(PeriodicTask)
admin.site.register(PeriodicTask, PeriodicTaskAdmin)

admin.site.unregister(Group)
admin.site.unregister(Site)
