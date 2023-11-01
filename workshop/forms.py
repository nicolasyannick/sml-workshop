from django import forms
from .models import Task, StateDuration, Worker

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['description','urgency','quantity','task_type','machining','assessment_hours']



class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = StateDuration
        fields = ['state','workers']

    state = forms.ChoiceField(choices=StateDuration.STATE_CHOICES, label='Status')
    workers = forms.ModelMultipleChoiceField(queryset=Worker.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)




class TaskFilterForm(forms.Form):
    # status = forms.MultipleChoiceField(choices=StateDuration.STATE_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)
    machining = forms.BooleanField(required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    urgency = forms.ChoiceField(choices=[('','Any')] + list(Task.URGENCY_CHOICES), required=False)


