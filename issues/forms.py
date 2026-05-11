from django import forms

from .models import Project, Issue, IssueRemarkLog
from .choices import IssueEnvironmentChoices, IssuePriorityChoices, IssueStatusChoices, IssueTypeChoices, UserModelChoiceField
from .models import Tag
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectForm(forms.ModelForm):
    owner = UserModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
    )

    class Meta:
        model = Project
        fields = [
            'name',
            'code',
            'description',
            'owner',
            'team',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'team': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class IssueForm(forms.ModelForm):
    priority = forms.ChoiceField(
        choices=IssuePriorityChoices.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    environment = forms.ChoiceField(
        choices=IssueEnvironmentChoices.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        choices=IssueStatusChoices.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    issue_type = forms.ChoiceField(
        choices=IssueTypeChoices.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    assignee = UserModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
    )

    class Meta:
        model = Issue
        fields = [
            'project',
            'title',
            'description',
            'drive_url',
            'issue_type',
            'reporter',
            'assignee',
            'priority',
            'environment',
            'status',
            'time_estimate_hours',
            'related_issue',
            'tags',
            'remarks',
            'qa_note',
            'image_1',
            'image_2',
            'image_3',
            'image_4',
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'drive_url': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_type': forms.Textarea(attrs={'class': 'form-control'}),
            'reporter': forms.Select(attrs={'class': 'form-select'}),
            'assignee': forms.Select(attrs={'class': 'form-select'}),
            'time_estimate_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'related_issue': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={"class": "form-select"}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'qa_note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'image_1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_3': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_4': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'related_issue' in self.fields:
            self.fields['related_issue'].queryset = Issue.objects.filter(
                issue_type=IssueTypeChoices.TASK
            )

class IssueRemarkLogForm(forms.ModelForm):
    class Meta:
        model = IssueRemarkLog
        fields = [
            'issue',
            'from_status',
            'to_status',
            'remark',
            'qa_note',
        ]
        widgets = {
            'issue': forms.HiddenInput(),
            'from_status': forms.Select(choices=IssueStatusChoices.choices, attrs={'class': 'form-control'}),
            'to_status': forms.Select(choices=IssueStatusChoices.choices, attrs={'class': 'form-control'}),
            'remark': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'qa_note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }