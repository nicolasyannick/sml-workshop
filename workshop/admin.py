from django.contrib import admin
from .models import WorkRequest, Worker, Expertise, CachedCalculation, Task

# Register your models here.

admin.site.register(WorkRequest)
admin.site.register(Worker)
admin.site.register(Expertise)
admin.site.register(CachedCalculation)
admin.site.register(Task)


