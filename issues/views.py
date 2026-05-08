from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .forms import ProjectForm, IssueForm, IssueRemarkLogForm
from .models import IssueRemarkLog, Project, Issue


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'issues/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.select_related('owner', 'team').all()


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'issues/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        return Project.objects.select_related('owner', 'team')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        context['issues'] = project.issues.select_related('assignee', 'reporter').all()
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'issues/project_form.html'

    def form_valid(self, form):
        project = form.save(commit=False)
        project.created_by = self.request.user
        project.save()
        return redirect('issues:project_detail', pk=project.pk)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'issues/project_form.html'
    context_object_name = 'project'

    def form_valid(self, form):
        project = form.save()
        return redirect('issues:project_detail', pk=project.pk)


class IssueListView(LoginRequiredMixin, ListView):
    model = Issue
    template_name = 'issues/issue_list.html'
    context_object_name = 'issues'

    def get_queryset(self):
        qs = Issue.objects.select_related('project', 'assignee', 'reporter').all()
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(project__name__icontains=search)
                | Q(assignee__username__icontains=search)
                | Q(reporter__username__icontains=search)
            )

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        # from dashboard cards:
        # ?assigned=1  -> only issues that have an assignee
        assigned = self.request.GET.get('assigned')
        if assigned == '1':
            qs = qs.filter(assignee__isnull=False)

        # ?priority=high / medium / low / critical
        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority=priority)

        # ?issue_type=task / bug / ...
        issue_type = self.request.GET.get('issue_type')
        if issue_type:
            qs = qs.filter(issue_type=issue_type)

        for issue in qs:
            issue.can_edit = issue.is_authorized(self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q')
        return context

class IssueDetailView(LoginRequiredMixin, DetailView):
    model = Issue
    template_name = 'issues/issue_detail.html'
    context_object_name = 'issue'


    def get_queryset(self):
        return Issue.objects.select_related('project', 'assignee', 'reporter')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        issue = self.object
        issue.can_edit = issue.is_authorized(self.request.user)
        context['remark_form'] = IssueRemarkLogForm(initial={'issue': issue})
        context['remark_logs'] = issue.remark_logs.select_related('author').all()
        return context


class IssueCreateView(LoginRequiredMixin, View):
    def get(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        form = IssueForm(initial={'project': project, 'reporter': request.user})
        return render(
            request,
            'issues/issue_form.html',
            {
                'form': form,
                'project': project,
            },
        )

    def post(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        form = IssueForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.project = project
            issue.created_by = request.user
            issue.reporter = request.user 
            issue.save()
            return redirect('issues:issue_detail', pk=issue.pk)
        return render(
            request,
            'issues/issue_form.html',
            {
                'form': form,
                'project': project,
            },
        )

class IssueUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        issue = get_object_or_404(Issue, pk=pk)
        form = IssueForm(instance=issue)
        form.fields['reporter'].widget.attrs['readonly'] = True
        return render(
            request,
            'issues/issue_form.html',
            {
                'form': form,
                'project': issue.project,
                'issue': issue,
            },
        )

    def post(self, request, pk):
        issue = get_object_or_404(Issue, pk=pk)
        old_status = issue.status
        old_priority = issue.priority
        old_status_label = issue.get_status_display()
        old_priority_label = issue.get_priority_display()

        form = IssueForm(request.POST, request.FILES, instance=issue)
        if form.is_valid():
            issue = form.save()

            if old_status != issue.status:
                IssueRemarkLog.objects.create(
                    issue=issue,
                    author=request.user,
                    from_status=old_status,
                    to_status=issue.status,
                    remark=f"Status changed from {old_status_label} to {issue.get_status_display()}.",
                )

            if old_priority != issue.priority:
                IssueRemarkLog.objects.create(
                    issue=issue,
                    author=request.user,
                    from_status=issue.status,
                    to_status=issue.status,
                    remark=f"Priority changed from {old_priority_label} to {issue.get_priority_display()}.",
                )

            return redirect('issues:issue_detail', pk=issue.pk)

        return render(
            request,
            'issues/issue_form.html',
            {
                'form': form,
                'project': issue.project,
                'issue': issue,
            },
        )


class IssueAddRemarkView(LoginRequiredMixin, View):
    def post(self, request, pk):
        issue = get_object_or_404(Issue, pk=pk)
        form = IssueRemarkLogForm(request.POST)
        if form.is_valid():
            remark_log = form.save(commit=False)
            remark_log.issue = issue
            remark_log.author = request.user
            remark_log.from_status = issue.status
            remark_log.to_status = form.cleaned_data.get('to_status') or issue.status
            remark_log.save()

            if remark_log.to_status and remark_log.to_status != issue.status:
                issue.status = remark_log.to_status
                issue.save(update_fields=['status', 'updated_at'])

        return redirect('issues:issue_detail', pk=issue.pk)

    def get(self, request, pk):
        return redirect('issues:issue_detail', pk=pk)
    



class MyIssueListView(LoginRequiredMixin, ListView):
    model = Issue
    template_name = 'issues/my_task.html'
    context_object_name = 'issues'

    def get_queryset(self):
        qs = Issue.objects.select_related('project', 'assignee', 'reporter').filter(
            assignee=self.request.user
        )
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(project__name__icontains=search)
                | Q(assignee__username__icontains=search)
                | Q(reporter__username__icontains=search)
            )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        for issue in qs:
            issue.can_edit = issue.is_authorized(self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q')
        return context