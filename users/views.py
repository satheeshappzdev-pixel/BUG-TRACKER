from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)

from issues.choices import IssuePriorityChoices, IssueStatusChoices
from issues.models import Issue, IssueRemarkLog, Project

from .forms import TeamForm, TeamMemberForm
from .models import Team, TeamMember
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Q, Count
from issues.models import Project, Issue, IssueRemarkLog


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.request.GET.get('project')

        context['projects'] = Project.objects.all()
        context['selected_project_id'] = project_id

        if project_id:
            issues_qs = Issue.objects.filter(project_id=project_id)
            recent_activities_qs = IssueRemarkLog.objects.select_related('issue', 'author').filter(
                issue__project_id=project_id,
            )
        else:
            issues_qs = Issue.objects.all()
            recent_activities_qs = IssueRemarkLog.objects.select_related('issue', 'author').all()

        context['active_bugs'] = issues_qs.filter(
            status=IssueStatusChoices.OPEN,
        ).count()

        context['active_tasks'] = issues_qs.filter(
            status=IssueStatusChoices.OPEN,
            assignee__isnull=False,
        ).count()

        context['high_priority_bugs'] = issues_qs.filter(
            status=IssueStatusChoices.OPEN,
            priority=IssuePriorityChoices.HIGH,
        ).count()

        context['my_open_issues'] = issues_qs.filter(
            status=IssueStatusChoices.OPEN,
            assignee=self.request.user,
        ).count()

        context['recent_activities'] = recent_activities_qs.order_by('-created_at')[:10]

        raw_status_stats = (
            issues_qs
            .values('status')
            .order_by('status')
            .annotate(count=Count('id'))
        )
        status_count_map = {item['status']: item['count'] for item in raw_status_stats}

        context['issue_status_stats'] = [
            {
                'value': choice.value,
                'label': choice.label,
                'count': status_count_map.get(choice.value, 0),
            }
            for choice in IssueStatusChoices
        ]

        # expose enums so template can use their .value
        context['IssueStatusChoices'] = IssueStatusChoices
        context['IssuePriorityChoices'] = IssuePriorityChoices

        return context

class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = 'users/team_list.html'
    context_object_name = 'teams'
    ordering = ['-created_at']


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = 'users/team_form.html'
    success_url = reverse_lazy('users:team_list')


class TeamUpdateView(LoginRequiredMixin, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = 'users/team_form.html'
    success_url = reverse_lazy('users:team_list')


class TeamDeleteView(LoginRequiredMixin, DeleteView):
    model = Team
    template_name = 'users/team_confirm_delete.html'
    success_url = reverse_lazy('users:team_list')


class TeamMemberListView(LoginRequiredMixin, ListView):
    model = TeamMember
    template_name = 'users/teammember_list.html'
    context_object_name = 'members'
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('user').filter(user__is_superuser=False)


class TeamMemberCreateView(LoginRequiredMixin, CreateView):
    model = TeamMember
    form_class = TeamMemberForm
    template_name = 'users/teammember_form.html'
    success_url = reverse_lazy('users:teammember_list')


class TeamMemberUpdateView(LoginRequiredMixin, UpdateView):
    model = TeamMember
    form_class = TeamMemberForm
    template_name = 'users/teammember_form.html'
    success_url = reverse_lazy('users:teammember_list')


class TeamMemberDeleteView(LoginRequiredMixin, DeleteView):
    model = TeamMember
    template_name = 'users/teammember_confirm_delete.html'
    success_url = reverse_lazy('users:teammember_list')