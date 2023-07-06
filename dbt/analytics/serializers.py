from django_celery_beat.models import IntervalSchedule, CrontabSchedule
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField
from rest_framework.exceptions import ValidationError
from dbt.analytics.models import (
    GitRepo,
    ProfileYAML,
    SSHKey,
    PeriodicTask as PeriodicTaskModel,
)
from dbt.utils.common import clone_git_repo


class GitRepoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitRepo
        fields = "__all__"

    def create(self, validated_data):
        repo = GitRepo.objects.create(**validated_data)
        result, msg = clone_git_repo(repo)
        if result:
            return repo
        else:
            # delete the repo from db
            repo.delete()
            raise ValidationError(detail=f"Error creating repo: {msg}")

    def update(self, instance, validated_data):
        result, msg = clone_git_repo(validated_data)
        if result:
            instance = super().update(instance, validated_data)
            clone_git_repo(instance)
            return instance
        else:
            raise ValidationError(detail=f"{msg}")


class ProfileYAMLSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileYAML
        fields = "__all__"


class SSHKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = SSHKey
        fields = "__all__"


class IntervalScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntervalSchedule
        fields = "__all__"


class PeriodicTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodicTaskModel
        fields = "__all__"


class CrontabScheduleSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)

    class Meta:
        model = CrontabSchedule
        fields = "__all__"


class WritePeriodicTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodicTaskModel
        fields = (
            "name",
            "enabled",
            "task",
            "description",
            "start_time",
            "crontab",
            "one_off",
            "args",
            "git_repo",
            "profile_yml",
        )


class DBTCurrentVersionSerializer(serializers.Serializer):
    module_name = serializers.CharField()
    version = serializers.CharField(allow_null=True)


class RunTaskSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()

    def validate_task_id(self, value):
        if not PeriodicTaskModel.objects.filter(id=value).exists():
            raise serializers.ValidationError('Task with this ID does not exist.')
        return value

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        task = PeriodicTaskModel.objects.get(id=instance['task_id'])
        ret['args'] = task.args
        return ret

