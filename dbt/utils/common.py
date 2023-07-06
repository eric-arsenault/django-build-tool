import os
import subprocess
import yaml
import re
from importlib.metadata import version, PackageNotFoundError
from django.conf import settings


def save_profile_yml(profile_yml_text_content, profile_dir):
    profile_yml_file = os.path.join(os.getenv("HOME"), profile_dir)
    dct = yaml.safe_load(profile_yml_text_content)
    print(f"Profile yml file: {profile_yml_file}")
    print(profile_yml_text_content)
    with open(profile_yml_file, "w") as file:
        yaml.dump(dct, file)


def clone_git_repo(instance) -> (bool, str):
    os.environ["PATH"] += os.pathsep + "/usr/bin"
    os.environ["PATH"] += os.pathsep + "/bin"
    EXTERNAL_REPO_PREFIX = getattr(settings, "EXTERNAL_REPO_PREFIX")
    THIS_PROJECT_PATH = getattr(settings, "THIS_PROJECT_PATH")
    EXTERNAL_REPO_NAME = "{}-{}".format(EXTERNAL_REPO_PREFIX, instance.id)
    destination = os.path.join(THIS_PROJECT_PATH, EXTERNAL_REPO_NAME)
    print(EXTERNAL_REPO_PREFIX, THIS_PROJECT_PATH, EXTERNAL_REPO_NAME, destination)
    if os.path.isdir(destination):  # if exist
        subprocess.run(["rm", "-rf", destination], check=True, capture_output=True)

    if instance.url.startswith("git"):
        pvt_key = os.path.join(
            os.getenv("HOME"),
            ".ssh/{}{}".format(
                getattr(settings, "SSH_KEY_PREFIX"), instance.ssh_key.id
            ),
        )
        cmd = 'eval "$(/usr/bin/ssh-agent -s)" && /usr/bin/ssh-add {} && /usr/bin/git clone {} {}'.format(
            pvt_key, instance.url, destination
        )
    else:
        cmd = "/usr/bin/git clone {} {}".format(instance.url, destination)

    print(cmd)
    p1 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    print(p1.stderr, "===")
    result = True
    msg = ""
    if re.search("fatal:", p1.stderr.decode("UTF-8")):
        result = False
        msg = p1.stderr.decode("UTF-8")
    return result, msg


# return current installed dbt version
def load_dbt_current_version() -> list[dict[str, str | None]]:
    module_names_list = [
        "dbt-core",
        "dbt-postgres",
        "dbt-redshift",
        "dbt-snowflake",
        "dbt-bigquery",
    ]
    modules_version_data = []
    for module_name in module_names_list:
        try:
            module_version = version(module_name)
        except PackageNotFoundError:
            module_version = None

        modules_version_data.append(
            {"module_name": module_name, "version": module_version}
        )
    return modules_version_data
