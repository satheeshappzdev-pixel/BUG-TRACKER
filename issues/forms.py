from django import forms

from .models import Project, Issue, IssueRemarkLog
from .choices import IssueEnvironmentChoices, IssuePriorityChoices, IssueStatusChoices, IssueTypeChoices


class ProjectForm(forms.ModelForm):
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


    class Meta:
        model = Issue
        fields = [
            'project',
            'title',
            'description',
            'issue_type',
            'reporter',
            'assignee',
            'priority',
            'environment',
            'status',
            'time_estimate_hours',
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
            'reporter': forms.Select(attrs={'class': 'form-select'}),
            'assignee': forms.Select(attrs={'class': 'form-select'}),
            'time_estimate_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'qa_note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'image_1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_3': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_4': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


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