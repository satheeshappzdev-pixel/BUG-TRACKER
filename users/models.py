from django.db import models
from django.conf import settings    
from django.contrib.auth.models import AbstractUser


from users.choices import TeamMemberRoleChoices



class User(AbstractUser):
    # optional extra fields here
    pass


class Team(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=15, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name



class TeamMember(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_member",
    )
    role = models.CharField(
        max_length=15,
        choices=TeamMemberRoleChoices.choices,
        blank=True,
    )
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, blank=True)
    date_joined_company = models.DateField(null=True, blank=True)
    is_active_developer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def has_management_role(self):
        return self.role in getattr(settings, 'MANAGEMENT_ROLES', [])


    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username})"