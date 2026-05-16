from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from issues.choices import IssueEnvironmentChoices, IssuePriorityChoices, IssueStatusChoices, IssueTypeChoices, TeamMemberRoleChoices
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
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from .models import Project, IssueStatusChoices


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
        
        # 1. Time Filtering Logic
        period = self.request.GET.get('period', 'all')
        now = timezone.now()
        issues_qs = project.issues.select_related('assignee', 'reporter', 'assignee__team_member', 'reporter__team_member')

        if period == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            filtered_qs = issues_qs.filter(created_at__gte=start_date)
        elif period == 'weekly':
            start_date = now - timedelta(days=7)
            filtered_qs = issues_qs.filter(created_at__gte=start_date)
        else:
            filtered_qs = issues_qs

        # 2. Status Annotation Helper
        status_choices = IssueStatusChoices.choices
        status_annotations = {
            f"{status.lower()}_count": Count('id', filter=Q(status=status)) 
            for status, label in status_choices
        }

        # 3. Developer Summary (Grouped by Assignee)
        dev_summary_qs = filtered_qs.values(
            'assignee__username', 'assignee__id', 'assignee__first_name', 'assignee__last_name'
        ).annotate(
            total=Count('id'),
            high_priority=Count('id', filter=Q(priority='high')),
            **status_annotations
        ).filter(
            Q(assignee__team_member__role='developer') | Q(assignee__team_member__role__isnull=True)
        ).exclude(assignee__team_member__role='qa').order_by('-total')

        # 4. QA Summary (Grouped by Reporter)
        qa_summary_qs = filtered_qs.values(
            'reporter__username', 'reporter__id', 'reporter__first_name', 'reporter__last_name'
        ).annotate(
            total=Count('id'),
            high_priority=Count('id', filter=Q(priority='high')),
            **status_annotations
        ).filter(reporter__team_member__role='qa').order_by('-total')

        # 5. Transformation Logic
        def process_summary(summary_qs, user_prefix, is_qa=False):
            processed = []
            for entry in summary_qs:
                u_id = entry.get(f'{user_prefix}__id')
                if not u_id: continue

                # --- CUSTOM PENDING LOGIC ---
                if is_qa:
                    # For QA, "Pending" are issues THEY reported that are now READY FOR QA
                    entry['pending_label'] = "Ready for QA"
                    entry['total_pending_all_time'] = project.issues.filter(
                        reporter_id=u_id, 
                        status='ready_for_qa' # Slug from your IssueStatusChoices
                    ).count()
                else:
                    # For Devs, "Pending" is their overall workload (not done/closed)
                    entry['pending_label'] = "Total Workload"
                    entry['total_pending_all_time'] = project.issues.filter(
                        assignee_id=u_id
                    ).exclude(status__in=['done', 'closed', 'ready_for_qa']).count()

                # Name & Status Lists
                first = entry.get(f'{user_prefix}__first_name')
                last = entry.get(f'{user_prefix}__last_name')
                entry['full_display_name'] = f"{first} {last}" if first and last else (first or entry.get(f'{user_prefix}__username'))
                
                entry['status_counts_list'] = [
                    {'label': label, 'count': entry.get(f"{status.lower()}_count", 0), 'slug': status.lower()}
                    for status, label in status_choices
                ]
                processed.append(entry)
            return processed

        context.update({
            'dev_summary': process_summary(dev_summary_qs, 'assignee', is_qa=False),
            'qa_summary': process_summary(qa_summary_qs, 'reporter', is_qa=True),
            'issues': filtered_qs.order_by('-created_at')[:10],
            'metrics': filtered_qs.aggregate(total=Count('id'), high_priority=Count('id', filter=Q(priority='high')), **status_annotations),
            'current_period': period,
            'status_choices': status_choices
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
    paginate_by = 50  # <-- Set pagination limit to 50 items per page

    def get_queryset(self):
        qs = Issue.objects.select_related('project', 'assignee', 'reporter').prefetch_related('tags')

        search = self.request.GET.get('q', '').strip()
        if search:
            query = (
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(project__name__icontains=search)
                | Q(assignee__username__icontains=search)
                | Q(reporter__username__icontains=search)
                | Q(tags__name__icontains=search)
            )

            if "-" in search:
                parts = search.split("-")
                prefix = parts[0]
                suffix = parts[1]
                if suffix.isdigit():
                    query |= Q(project__code__iexact=prefix, pk=suffix)

            clean_id = search.replace('#', '')
            if clean_id.isdigit():
                query |= Q(pk=clean_id)

            qs = qs.filter(query).distinct()

        # Status filtering
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
        if project_id:  
            qs = qs.filter(project_id=project_id)

        environment = self.request.GET.get('environment')
        if environment:
            qs = qs.filter(environment=environment)

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

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Inject authorization attributes into the current page's slice dynamically
        for issue in context['issues']:
            issue.can_edit = issue.is_authorized(self.request.user)

        # Build clean query string for pagination to keep your search filters intact across pages
        queries_without_page = self.request.GET.copy()
        if 'page' in queries_without_page:
            del queries_without_page['page']
        context['current_filters'] = queries_without_page.urlencode()

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
    paginate_by = 50  # <-- Set pagination limit to 50 items per page

    def get_queryset(self):
        user = self.request.user
        
        # Safe Check: Prevent RelatedObjectDoesNotExist if user has no profile
        if hasattr(user, 'team_member'):
            role = user.team_member.role
        else:
            role = None
        
        # Filter logic based on team assignment profile
        if role == TeamMemberRoleChoices.QA:
            qs = Issue.objects.filter(reporter=user)
        elif role == TeamMemberRoleChoices.DEVELOPER:
            qs = Issue.objects.filter(assignee=user)
        else:
            # Fallback for Admins / Staff without an explicit profile: See both
            qs = Issue.objects.filter(Q(assignee=user) | Q(reporter=user))

        # Apply Time Filter
        date_filter = self.request.GET.get('date_filter')
        now = timezone.now()
        if date_filter == 'day':
            qs = qs.filter(created_at__gte=now - timedelta(days=1))
        elif date_filter == 'week':
            qs = qs.filter(created_at__gte=now - timedelta(weeks=1))
        elif date_filter == 'month':
            qs = qs.filter(created_at__gte=now - timedelta(days=30))

        # Apply Status Filter
        status = self.request.GET.get('status')
        if status:
            if status == 'pending_qa':
                qs = qs.filter(status='ready_for_qa')
            else:
                qs = qs.filter(status=status)
            
        return qs.select_related('project', 'assignee', 'reporter').prefetch_related('tags').distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Safe check inside context data configuration
        if hasattr(user, 'team_member'):
            role = user.team_member.role
            context['view_perspective'] = user.team_member.get_role_display()
        else:
            role = None
            context['view_perspective'] = "Staff / Admin"
        
        # Build clean query string parameter preservation for pagination loops
        queries_without_page = self.request.GET.copy()
        if 'page' in queries_without_page:
            del queries_without_page['page']
        context['current_filters'] = queries_without_page.urlencode()

        # Summary Metrics Evaluation Base Line
        if role == TeamMemberRoleChoices.QA:
            metrics_qs = Issue.objects.filter(reporter=user)
        elif role == TeamMemberRoleChoices.DEVELOPER:
            metrics_qs = Issue.objects.filter(assignee=user)
        else:
            metrics_qs = Issue.objects.filter(Q(assignee=user) | Q(reporter=user))

        # Align metrics tracking indicators seamlessly with active timeline viewports
        date_filter = self.request.GET.get('date_filter')
        now = timezone.now()
        if date_filter == 'day':
            metrics_qs = metrics_qs.filter(created_at__gte=now - timedelta(days=1))
        elif date_filter == 'week':
            metrics_qs = metrics_qs.filter(created_at__gte=now - timedelta(weeks=1))
        elif date_filter == 'month':
            metrics_qs = metrics_qs.filter(created_at__gte=now - timedelta(days=30))

        context['metrics'] = metrics_qs.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status='open')),
            pending_qa=Count('id', filter=Q(status='ready_for_qa')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            critical=Count('id', filter=Q(priority='high'))
        )
        
        context['current_status'] = self.request.GET.get('status', '')
        context['current_date_filter'] = self.request.GET.get('date_filter', 'all')
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