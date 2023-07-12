import json
import os
from django.core.management import call_command
from celery import Celery, shared_task

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("dbt")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@shared_task
@app.task(
    bind=True, name="dbt_runner_task")
def dbt_runner_task(self, *args, **kwargs):
    option = "--dbt_command={}".format(self.request.args[0])
    option_two = "--pk={}".format(self.request.kwargs)  # pk is git repo object id
    call_command("dbt_command", option, option_two)


@app.task(bind=True)
def dbt_to_db(self):
    call_command("dbt_to_db")
