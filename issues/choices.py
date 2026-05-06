from django.db import models


class IssuePriorityChoices(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class IssueStatusChoices(models.TextChoices):
    OPEN = 'open', 'Open'
    IN_PROGRESS = 'in_progress', 'In Progress'
    HOLD = 'hold', 'Hold' 
    SCOPE_REVIEW = 'scope_review', 'Scope Review'
    REJECTED = 'rejected', 'Rejected'
    IN_REVIEW = 'in_review', 'In Review'
    QA = 'qa', 'QA'
    DONE = 'done', 'Done'
    CLOSED = 'closed', 'Closed'
    REOPEN = 'reopen', 'Reopen'

class IssueEnvironmentChoices(models.TextChoices):
    LOCAL = 'local', 'Local'
    STAGING = 'staging', 'Staging'
    UAT = 'uat', 'UAT'
    PRODUCTION = 'production', 'Production'

class TeamMemberRoleChoices(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    DEVELOPER = "developer", "Developer"
    QA = "qa", "QA"

class IssueTypeChoices(models.TextChoices):
    BUG = "bug", "Bug"
    TASK = "task", "Task"
    ENHANCEMENT = "enhancement", "Enhancement"