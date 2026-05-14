from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from issues.choices import IssueEnvironmentChoices, IssuePriorityChoices, IssueStatusChoices, IssueTypeChoices

from django.db.models import Q, Count
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Issue


from django.contrib.auth import get_user_model
from .forms import ProjectForm, IssueForm, IssueRemarkLogForm
from .models import IssueRemarkLog, Project, Issue

from .forms import TagForm
from .models import Tag
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Project, Issue
from .models import Issue


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
        return Project.objects.select_related('owner')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        
        # 1. Handle Time Filtering
        period = self.request.GET.get('period', 'all')
        now = timezone.now()
        issues_qs = project.issues.select_related('assignee')

        if period == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            issues_qs = issues_qs.filter(created_at__gte=start_date)
        elif period == 'weekly':
            start_date = now - timedelta(days=7)
            issues_qs = issues_qs.filter(created_at__gte=start_date)

        # 2. Dynamic Annotation for all Statuses
        status_annotations = {
            f"{status.lower()}_count": Count('id', filter=Q(status=status))
            for status, label in IssueStatusChoices.choices
        }

        # Added first_name and last_name to values()
        member_summary_qs = issues_qs.values(
            'assignee__username', 
            'assignee__id',
            'assignee__first_name',
            'assignee__last_name'
        ).annotate(
            total=Count('id'),
            high_priority=Count('id', filter=Q(priority='high')),
            **status_annotations
        ).order_by('-total')

        # Convert QuerySet to list to modify objects for the template
        member_summary = list(member_summary_qs)

        # 3. Data Transformation (Removing need for get_item tag)
        for member in member_summary:
            # --- Logic to create full name ---
            first = member.get('assignee__first_name')
            last = member.get('assignee__last_name')
            if first and last:
                member['full_display_name'] = f"{first} {last}"
            elif first:
                member['full_display_name'] = first
            else:
                member['full_display_name'] = member.get('assignee__username') or "Unassigned"
            # ---------------------------------

            counts_list = []
            for status, label in IssueStatusChoices.choices:
                key = f"{status.lower()}_count"
                counts_list.append({
                    'label': label,
                    'count': member.get(key, 0),
                    'slug': status.lower() # For CSS class mapping
                })
            member['status_counts_list'] = counts_list

        # 4. Overall Metrics
        metrics = issues_qs.aggregate(
            total=Count('id'),
            high_priority=Count('id', filter=Q(priority='high')),
            **status_annotations
        )

        context.update({
            'issues': issues_qs.order_by('-created_at')[:10],
            'member_summary': member_summary,
            'metrics': metrics,
            'current_period': period,
            'status_choices': IssueStatusChoices.choices
        })
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
        qs = Issue.objects.select_related('project', 'assignee', 'reporter').prefetch_related('tags')

        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(project__name__icontains=search)
                | Q(assignee__username__icontains=search)
                | Q(reporter__username__icontains=search)
                | Q(tags__name__icontains=search)
            ).distinct()

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority=priority)

        issue_type = self.request.GET.get('issue_type')
        if issue_type:
            qs = qs.filter(issue_type=issue_type)

        project_id = self.request.GET.get('project')
        if project_id:  # Handles non-empty project ID
            qs = qs.filter(project_id=project_id)

        environment = self.request.GET.get('environment')
        if environment:
            qs = qs.filter(environment=environment)

        # Handle source=MINE (Issues involving the current user)
        source = self.request.GET.get('source')
        if source == 'MINE':
            qs = qs.filter(Q(assignee=self.request.user) | Q(reporter=self.request.user))

        assignee_id = self.request.GET.get('assignee')
        if assignee_id:
            if assignee_id == 'me':
                qs = qs.filter(assignee=self.request.user)
            else:
                qs = qs.filter(assignee_id=assignee_id)

        reporter_id = self.request.GET.get('reporter')
        if reporter_id:
            if reporter_id == 'me':
                qs = qs.filter(reporter=self.request.user)
            else:
                qs = qs.filter(reporter_id=reporter_id)

        assigned_only = self.request.GET.get('assigned')
        if assigned_only == '1':
            qs = qs.filter(assignee__isnull=False)

        related_filter = self.request.GET.get('related_filter')
        if related_filter == 'has':
            qs = qs.filter(related_issue__isnull=False)
        elif related_filter == 'none':
            qs = qs.filter(related_issue__isnull=True)

        related_issue_id = self.request.GET.get('related_issue')
        if related_issue_id:
            qs = qs.filter(related_issue_id=related_issue_id)

        # Apply authorization flag to results
        for issue in qs:
            issue.can_edit = issue.is_authorized(self.request.user)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Persist state in template
        context['search'] = self.request.GET.get('q')
        context['selected_project_id'] = self.request.GET.get('project')
        context['selected_source'] = self.request.GET.get('source')

        # Dropdown data for filters
        context['projects'] = Project.objects.all()
        context['assignees'] = (
            get_user_model()
            .objects.filter(assigned_issues__isnull=False)
            .distinct()
        )
        context['reporters'] = (
            get_user_model()
            .objects.filter(reported_issues__isnull=False)
            .distinct()
        )
        # Related tasks lookup
        context['related_issues'] = Issue.objects.filter(
            issue_type=IssueTypeChoices.TASK
        ).order_by('title')

        # Expose Choice Enums to Template
        context['IssueStatusChoices'] = IssueStatusChoices
        context['IssuePriorityChoices'] = IssuePriorityChoices
        context['IssueEnvironmentChoices'] = IssueEnvironmentChoices
        context['IssueTypeChoices'] = IssueTypeChoices

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
        # 1. Base Queryset for the logged in user
        qs = Issue.objects.select_related('project', 'assignee', 'reporter').filter(
            assignee=self.request.user
        )
        
        # 2. Search Logic
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(project__name__icontains=search)
            )
            
        # 3. Status Filter Logic (Top Bar)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        # 4. Permission tagging
        for issue in qs:
            issue.can_edit = issue.is_authorized(self.request.user)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aggregated counts for the summary bar
        user_issues = Issue.objects.filter(assignee=self.request.user)
        context['summary'] = user_issues.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status='open')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            done=Count('id', filter=Q(status='done'))
        )
        
        context['search'] = self.request.GET.get('q')
        context['current_status'] = self.request.GET.get('status')
        return context
    

class TagListView(LoginRequiredMixin, View):
    def get(self, request):
        tags = Tag.objects.all()
        return render(request, "tags/tag_list.html", {"tags": tags})


class TagCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = TagForm()
        return render(request, "tags/tag_form.html", {"form": form, "title": "Create Tag"})

    def post(self, request):
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("issues:tag_list")
        return render(request, "tags/tag_form.html", {"form": form, "title": "Create Tag"})


class TagUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        form = TagForm(instance=tag)
        return render(request, "tags/tag_form.html", {"form": form, "title": "Edit Tag"})

    def post(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            return redirect("issues:tag_list")
        return render(request, "tags/tag_form.html", {"form": form, "title": "Edit Tag"})


class TagDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        return render(request, "tags/tag_confirm_delete.html", {"tag": tag})

    def post(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        tag.delete()
        return redirect("issues:tag_list")