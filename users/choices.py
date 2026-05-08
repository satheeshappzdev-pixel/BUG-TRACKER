from django.db import models


class TeamMemberRoleChoices(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    DEVELOPER = "developer", "Developer"
    QA = "qa", "QA"