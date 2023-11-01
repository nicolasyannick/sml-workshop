from django.db import models
from django.utils import timezone

# Create your models here.

class Expertise(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Worker(models.Model):
    name=models.CharField(max_length=100)
    WORKER_TYPE_CHOICES = [
        ('Local','Local'),
        ('Expat','Expat')
    ]
    worker_type = models.CharField(max_length=10, choices=WORKER_TYPE_CHOICES)
    pay_rate = models.FloatField()
    expertise = models.ManyToManyField(Expertise)

    def __str__(self):
        return self.name


class WorkRequest(models.Model):
    UNIT_CHOICES = [
        ('FM1', 'FM1'),
        ('FM2', 'FM2'),
        ('FMM', 'FMM'),
        ('HO', 'Head Office'),
        ('KNT', 'KNT'),
        ('NP5', 'NP5'),
        ('SML', 'SML'),
    ]
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    DEPT_CHOICES = [
        ('',''),
        ('AUTO','Automotive'),
        ('ELEC','Electrical'),
        ('HR','HR'),
        ('MAINT','Maintenance'),
        ('RND','RnD'),
        ('UTL','Utility'),
    ]
    department = models.CharField(max_length=50, blank=True, choices=DEPT_CHOICES)
    date = models.DateField()
    requester = models.CharField(max_length=50)

    def __str__(self):
        return f"Request from '{self.requester}', '{self.unit}' received on '{self.date}'"


class Task(models.Model):
    work_request = models.ForeignKey(WorkRequest, related_name='tasks', on_delete=models.CASCADE)
    description = models.TextField()
    URGENCY_CHOICES=[
        (1,'1 Week'),
        (2,'3 Days'),
        (3,'1 Day')
    ]
    urgency = models.IntegerField(choices=URGENCY_CHOICES)
    quantity = models.IntegerField()
    TASK_TYPE_CHOICES = [
        (1,'Repair'),
        (2,'Modification'),
        (3,'Fabrication'),
        (4,'Other')
    ]
    task_type = models.IntegerField(choices=TASK_TYPE_CHOICES)
    machining = models.BooleanField(default=False)
    assessment_hours = models.FloatField(blank=True, null=True)
    assessment_time = models.DurationField(blank=True, null=True)
    is_planned = models.BooleanField(default=False)

    STATE_CHOICES = [
        (1,'New'),
        (2,'Queued'),
        (3,'Back Load'),
        (4,'Awaiting Material'),
        (5,'In Progress'),
        (6,'Completed'),
        (7,'Cancelled')
    ]
    current_status = models.IntegerField(choices=STATE_CHOICES, default=1)

    # def current_status(self):
    #     latest_state = self.stateduration_set.order_by('-start_time').first()
    #     return latest_state.get_state_display()


    
    def save(self, *args, **kwargs):

        super(Task, self).save(*args, **kwargs)

        #Checks if a StateDuration entry already exists
        if not self.stateduration_set.exists():
            #Create a new StateDuration entry with status "NEW"
            StateDuration.objects.create(
                task = self,
                state = 1,
                start_time = self.work_request.date,
                normal_duration = timezone.timedelta(minutes=0),
                overtime_duration = timezone.timedelta(minutes=0)
            )
            self.current_status = 1 
        
        
        latest_state = self.stateduration_set.order_by('-start_time').first()
        if latest_state:
            self.current_status = latest_state.state
            super(Task, self).save(*args, **kwargs)


        


class StateDuration(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    STATE_CHOICES = [
        (1,'New'),
        (2,'Queued'),
        (3,'Back Load'),
        (4,'Awaiting Material'),
        (5,'In Progress'),
        (6,'Completed'),
        (7,'Cancelled')
    ]
    state = models.IntegerField(choices=STATE_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    normal_duration = models.DurationField(null=True, blank=True)
    overtime_duration = models.DurationField(null=True, blank=True)
    workers = models.ManyToManyField(Worker)


class MaterialPurchase(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    material_name = models.CharField(max_length=100)
    quantity = models.FloatField()
    received = models.BooleanField(default=False)


class TaskReport(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE)
    total_time_spent = models.DurationField()
    total_manpower_cost = models.FloatField()
    total_material_cost = models.FloatField()


class MaterialUsed(models.Model):
    report = models.ForeignKey(TaskReport, related_name='materials_used', on_delete=models.CASCADE)
    material_name = models.CharField(max_length=100)
    quantity = models.FloatField()
    cost = models.FloatField()


class CachedCalculation(models.Model):
    date = models.DateField(unique=True, help_text="Date for which calculation is made")
    machining_workload = models.FloatField(help_text="Cummulative assessment time for all active machining tasks")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__ (self):
        return f"Calculation(s) for {self.date}"
    














