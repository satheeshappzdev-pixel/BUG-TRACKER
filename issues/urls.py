from django.urls import path
from .views import (
    MyIssueListView, ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView,
    IssueListView, IssueDetailView, IssueCreateView, IssueUpdateView, IssueAddRemarkView,
)

app_name = 'issues'

urlpatterns = [
    path('projects/', ProjectListView.as_view(), name='project_list'),
    path('projects/new/', ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/edit/', ProjectUpdateView.as_view(), name='project_update'),
    path('issues/', IssueListView.as_view(), name='issue_list'),
    path('issues/<int:pk>/', IssueDetailView.as_view(), name='issue_detail'),
    path('projects/<int:project_pk>/issues/new/', IssueCreateView.as_view(), name='issue_create'),
    path('issues/<int:pk>/edit/', IssueUpdateView.as_view(), name='issue_update'),
    path('issues/<int:pk>/remarks/add/', IssueAddRemarkView.as_view(), name='issue_add_remark'),
    path('my-tasks/', MyIssueListView.as_view(), name='my_issue_list'),
]