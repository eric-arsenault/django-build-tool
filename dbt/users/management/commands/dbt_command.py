import json
import os
import subprocess
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
import paramiko
from dbt.analytics.models import (
    Args,
    DBTLogs,
    GitRepo,
    SubProcessLog,
    ProfileYAML,
    PeriodicTask,
)
from dbt.utils.common import save_profile_yml

SSH_KEY_PREFIX = "git-django_"


class Command(BaseCommand):
    help = "DBT jobs"

    def add_arguments(self, parser):
        print("add_arguments", parser)
        parser.add_argument("--dbt_command", action="store", type=str)
        parser.add_argument(
            "--pk", action="store", type=str
        )  # pk is git repo object id

    def read_json(self, filename, pk):
        DBT_LOG_TARGET = "{}-{}/target".format(
            getattr(settings, "EXTERNAL_REPO_PREFIX"), pk
        )
        file_path = os.path.join(DBT_LOG_TARGET, filename)
        data = {}
        try:
            with open(file_path, "r") as state:
                data = json.load(state)
        except Exception:
            print(f"{file_path} not found")
            data = {}
        return data

    def handle(self, *args, **options):
        os.environ["PATH"] += os.pathsep + "/usr/bin"
        os.environ["PATH"] += os.pathsep + "/bin"
        try:
            dbt_command = options["dbt_command"]
            pk = json.loads(options["pk"].replace("'", '"'))["task_id"]

            if dbt_command.startswith("dbt"):
                instance = PeriodicTask.objects.get(id=pk)
                git_repo = GitRepo.objects.get(id=instance.git_repo_id)
                profile_yml = ProfileYAML.objects.get(id=instance.profile_yml_id)

                EXTERNAL_REPO_PREFIX = getattr(settings, "EXTERNAL_REPO_PREFIX")
                THIS_PROJECT_PATH = getattr(settings, "THIS_PROJECT_PATH")
                EXTERNAL_REPO_NAME = f"{EXTERNAL_REPO_PREFIX}-{instance.git_repo_id}"
                EXTERNAL_REPO_PATH = os.path.join(THIS_PROJECT_PATH, EXTERNAL_REPO_NAME)

                os.path.join(THIS_PROJECT_PATH, EXTERNAL_REPO_NAME)
                pull_cmd = f"cd {EXTERNAL_REPO_PATH} && git pull origin HEAD"
                print(f"Pull cmd: {pull_cmd}")

                profile_yml_content = None
                if instance.profile_yml:
                    profile_yml_content = profile_yml.profile_yml
                    save_profile_yml(profile_yml_content, ".dbt/profiles.yml")
                else:
                    print("No profile yml found")
                    exit(-1)

                if git_repo.url.startswith("git"):
                    pvt_key = os.path.join(
                        os.getenv("HOME"),
                        ".ssh/{}{}".format(SSH_KEY_PREFIX, git_repo.ssh_key.id),
                    )
                    cmd = 'eval "$(/usr/bin/ssh-agent -s)" && /usr/bin/ssh-add {} && {}'.format(
                        pvt_key, pull_cmd
                    )
                    p1 = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                    )
                else:
                    p1 = subprocess.Popen(
                        pull_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                    )
                p1.wait()
                SubProcessLog.objects.create(details=str(p1))
                p1.kill()
                del p1

                executable_command = "cd {} && {}".format(
                    EXTERNAL_REPO_PATH, dbt_command
                )
                dbt_result = subprocess.Popen(
                    executable_command,
                    cwd=EXTERNAL_REPO_PATH,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                dbt_result.wait()
                os.system("cd {} && git pull origin HEAD".format(EXTERNAL_REPO_PATH))

                manifest = self.read_json(
                    f"{EXTERNAL_REPO_PATH}/target/manifest.json", instance.git_repo_id
                )
                run_results = self.read_json(
                    f"{EXTERNAL_REPO_PATH}/target/run_results.json",
                    instance.git_repo_id,
                )
                sources = self.read_json(
                    f"{EXTERNAL_REPO_PATH}/target/sources.json", instance.git_repo_id
                )
                catalog = self.read_json(
                    f"{EXTERNAL_REPO_PATH}/target/catalog.json", instance.git_repo_id
                )

                dbt_log = DBTLogs.objects.create(
                    manifest=manifest,
                    run_results=run_results,
                    sources=sources,
                    catalog=catalog,
                    command=dbt_command,
                    repository_used_name=instance.git_repo.name,
                    profile_yml_used_name=profile_yml.name,
                    periodic_task_name=instance.name,
                    completed_at=datetime.now(),
                    previous_command="this is first commands"
                    if not DBTLogs.objects.all().exists()
                    else DBTLogs.objects.last().command,
                    dbt_stdout=dbt_result.stdout.read().decode("utf-8"),
                )

                args = run_results.get("args", {})
                Args.objects.create(
                    dbt_log=dbt_log,
                    quiet=args.get("quiet", ""),
                    which=args.get("which", ""),
                    no_print=args.get("no_print", ""),
                    rpc_method=args.get("rpc_method", ""),
                    use_colors=args.get("use_colors", ""),
                    write_json=args.get(" write_json", ""),
                    profiles_dir=args.get("profiles_dir", ""),
                    partial_parse=args.get("partial_parse", ""),
                    printer_width=args.get("printer_width", ""),
                    static_parser=args.get("static_parser", ""),
                    version_check=args.get("version_check", ""),
                    event_buffer_size=args.get("event_buffer_size", ""),
                    indirect_selection=args.get("indirect_selection", ""),
                    send_anonymous=args.get("send_anonymous_usage_stats", ""),
                    usage_stats=args.get("usage_stats", ""),
                )

                dbt_result.kill()
                del dbt_result

        except Exception as err:
            try:
                dbt_result.kill()
                del dbt_result
            except Exception as err:
                pass
            instance = PeriodicTask.objects.get(id=pk)
            DBTLogs.objects.create(
                command=dbt_command,
                periodic_task_name=instance.name,
                completed_at=datetime.now(),
                repository_used_name=instance.git_repo.name,
                profile_yml_used_name=profile_yml.name,
                previous_command="this is first commands"
                if not DBTLogs.objects.all().exists()
                else DBTLogs.objects.last().command,
                success=False,
                fail_reason=str(err),
            )
