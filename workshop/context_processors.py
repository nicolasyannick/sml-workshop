from .models import WorkRequest

def unit_choices(request):
    return {'UNIT_CHOICES': WorkRequest.UNIT_CHOICES}

def dept_choices(request):
    return {'DEPT_CHOICES': WorkRequest.DEPT_CHOICES}