from __future__ import annotations

from ansible_base.lib.abstract_models import AbstractOrganization, AbstractTeam
from django.conf import settings
from django.contrib.auth.models import Group as BaseGroup
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django_lifecycle import (
    AFTER_UPDATE,
    AFTER_DELETE,
    BEFORE_CREATE,
    BEFORE_DELETE,
    LifecycleModelMixin,
    hook,
)
from pulpcore.plugin.models import Group as PulpGroup

from galaxy_ng.app.models.auth import Group
from ansible_base.resource_registry.fields import AnsibleResourceField


class OrganizationManager(models.Manager):
    def get_default(self) -> Organization:
        """Return default organization."""
        return self.get(name=settings.DEFAULT_ORGANIZATION_NAME)


class Organization(LifecycleModelMixin, AbstractOrganization):
    """An organization model."""

    resource = AnsibleResourceField(primary_key_field="id")

    objects = OrganizationManager()

    class Meta(AbstractOrganization.Meta):
        permissions = [('member_organization', 'User is a member of this organization')]

    @hook(AFTER_UPDATE)
    def _after_update(self):
        if self.has_changed("name"):
            for team in self.teams.all():
                group = team.group
                group.name = team.group_name()
                group.save()

    @hook(BEFORE_DELETE)
    def _before_delete(self):
        for team in self.teams.all():
            team.delete()


class Team(LifecycleModelMixin, AbstractTeam):
    """A team model."""

    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="Related group record.",
    )

    resource = AnsibleResourceField(primary_key_field="id")

    # Team member permission is used by DAB RBAC
    class Meta(AbstractTeam.Meta):
        permissions = [('member_team', 'Has all permissions granted to this team')]

    def group_name(self):
        if self.organization.name == settings.DEFAULT_ORGANIZATION_NAME:
            return self.name
        return f"{self.organization.name}::{self.name}"

    @hook(BEFORE_CREATE)
    def _create_related_group(self, **kwargs):
        if hasattr(self, "group"):
            return
        self.group = Group(name=self.group_name())
        # NOTE(cutwater): This is a hack. Delete along with the signal handler below.
        self.group._x_skip_create_team = True
        self.group.save()

    @hook(AFTER_UPDATE)
    def _rename_related_group(self, **kwargs):
        if not self.has_changed("name"):
            return
        self.group.name = self.group_name()
        self.group.save()

    @hook(AFTER_DELETE)
    def _delete_related_group(self, **kwargs):
        group = getattr(self, "group", None)
        if group:
            group.delete()


@receiver(signal=signals.post_save, sender=Group)
@receiver(signal=signals.post_save, sender=PulpGroup)
@receiver(signal=signals.post_save, sender=BaseGroup)
def _create_related_team(sender, instance, created, **kwargs):
    if not created or getattr(instance, "_x_skip_create_team", False):
        return
    Team.objects.create(
        name=instance.name,
        organization=Organization.objects.get_default(),
        group=instance,
    )
