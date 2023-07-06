import os
import subprocess

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from dbt.analytics.models import GitRepo, SSHKey, PeriodicTask

SSH_KEY_PREFIX = getattr(settings, "SSH_KEY_PREFIX")

User = get_user_model()


# @receiver(post_save, sender=GitRepo)
def on_git_repo_save(sender, instance, created, **kwargs):
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
            os.getenv("HOME"), ".ssh/{}{}".format(SSH_KEY_PREFIX, instance.ssh_key.id)
        )
        cmd = 'eval "$(/usr/bin/ssh-agent -s)" && /usr/bin/ssh-add {} && /usr/bin/git clone {} {}'.format(
            pvt_key, instance.url, destination
        )
    else:
        cmd = "/usr/bin/git clone {} {}".format(instance.url, destination)

    print(cmd)
    p1 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    print(p1.stderr, "===")


@receiver(pre_delete, sender=GitRepo)
def on_gitrepo_delete(sender, instance, **kwargs):
    os.environ["PATH"] += os.pathsep + "/usr/bin"
    os.environ["PATH"] += os.pathsep + "/bin"
    EXTERNAL_REPO_PREFIX = getattr(settings, "EXTERNAL_REPO_PREFIX")
    THIS_PROJECT_PATH = getattr(settings, "THIS_PROJECT_PATH")
    EXTERNAL_REPO_NAME = "{}-{}".format(EXTERNAL_REPO_PREFIX, instance.id)
    destination = os.path.join(THIS_PROJECT_PATH, EXTERNAL_REPO_NAME)
    if os.path.isdir(destination):  # if exist
        subprocess.run(["rm", "-rf", destination], check=True, capture_output=True)


@receiver(post_save, sender=SSHKey)
def on_ssh_key_create(sender, instance, created, **kwargs):
    ssh_key_path = os.path.join(
        os.getenv("HOME"), ".ssh/{}{}".format(SSH_KEY_PREFIX, instance.id)
    )

    subprocess.run(
        ["/usr/bin/ssh-keygen", "-f", ssh_key_path, "-N", ""],
        check=False,
        capture_output=True,
    )


@receiver(pre_delete, sender=SSHKey)
def on_ssh_key_delete(sender, instance, **kwargs):
    os.environ["PATH"] += os.pathsep + "/usr/bin"
    os.environ["PATH"] += os.pathsep + "/bin"
    private_key = os.path.join(
        os.getenv("HOME"), ".ssh/{}{}".format(SSH_KEY_PREFIX, instance.id)
    )
    public_key = os.path.join(
        os.getenv("HOME"), ".ssh/{}{}.pub".format(SSH_KEY_PREFIX, instance.id)
    )

    subprocess.run(["rm", "-rf", private_key], check=True, capture_output=True)
    subprocess.run(["rm", "-rf", public_key], check=True, capture_output=True)


@receiver(post_save, sender=PeriodicTask)
def on_periodic_task_create(sender, instance, created, **kwargs):
    if created:
        instance.kwarg = {"task_id": instance.id}
        instance.save()
