import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from dbt.analytics.models import DBTLogs


class Command(BaseCommand):
    help = 'DBT jobs'

    def read_json(self, filename):

        DBT_LOG_TARGET = getattr(settings, 'DBT_LOG_TARGET')
        file_path = os.path.join(DBT_LOG_TARGET, filename)
        data = {}
        with open(file_path, 'r') as state:
            data = json.load(state)
        return data

    def handle(self, *args, **options):
        manifest = self.read_json('manifest.json')
        run_results = self.read_json('run_results.json')

        DBTLogs.objects.create(
            manifest=manifest,
            run_results=run_results,
        )
