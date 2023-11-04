from django.shortcuts import render, redirect, get_object_or_404
from .models import WorkRequest, Task, StateDuration, CachedCalculation
from .forms import TaskForm, TaskFilterForm, StatusUpdateForm
from .utils import calculate_duration_for_local, calculate_duration_for_expat
from datetime import timedelta, datetime, time
from django.contrib import messages
from django.utils import timezone
from django.utils.timezone import make_aware
from django.db.models import Sum
import pandas as pd
import plotly.express as px
import plotly.offline as pyo


# Create your views here.

# def home(request):
#     return render(request,'main.html')


def new_work_request(request):
    if request.method == 'POST':
        #Extract the data from POST request
        unit = request.POST.get('unit')
        department = request.POST.get('department')
        date = request.POST.get('date')
        requester = request.POST.get('requester')

        #Create a new WorkRequest object and save it to the database
        new_request = WorkRequest(unit=unit, department=department, date=date, requester=requester)
        new_request.save()

        #Redirect to the Request Page with Preloaded info
        return redirect('request_page', work_request_id=new_request.id)
    
    
def request_page(request, work_request_id):
    work_request = WorkRequest.objects.get(id=work_request_id)
    machining_tasks = Task.objects.filter(work_request = work_request, machining=True)
    non_machining_tasks = Task.objects.filter(work_request = work_request, machining = False)

    new_task_form = TaskForm(request.POST or None)

    if request.method == "POST":
        if new_task_form.is_valid():
            new_task = new_task_form.save(commit=False)
            new_task.work_request = work_request
            if new_task.assessment_hours is not None:
                new_task.assessment_time = timedelta(hours = new_task.assessment_hours)
            else:
                new_task.assessment_time = None
            new_task.save()

            return redirect('request_page', work_request_id=work_request_id)
    
    context ={
        'work_request': work_request,
        'machining_tasks': machining_tasks,
        'non_machining_tasks': non_machining_tasks,
        'new_task_form': new_task_form,
    }

    return render(request, 'request_page.html', context=context)



def status_update_page(request):
    # Handling the TasFilterForm
    task_filter_form = TaskFilterForm(request.GET or None)
    filtered_tasks = Task.objects.all()

    if task_filter_form.is_valid():
        # Apply filters based on form input
        # status = task_filter_form.cleaned_data['status']
        machining = task_filter_form.cleaned_data['machining']
        date_from = task_filter_form.cleaned_data['date_from']
        date_to = task_filter_form.cleaned_data['date_to']
        urgency = task_filter_form.cleaned_data['urgency']

        if machining is not None:
            filtered_tasks = filtered_tasks.filter(machining=machining)
        if date_from and date_to:
            filtered_tasks = filtered_tasks.filter(stateduration__start_time__range=[date_from, date_to])
        elif date_from:
            filtered_tasks = filtered_tasks.filter(stateduration__start_time__gte= date_from)
        elif date_to:
            filtered_tasks = filtered_tasks.filter(stateduration__start_time__lte= date_to)
        if urgency:
            filtered_tasks = filtered_tasks.filter(urgency=urgency)
        
        # if status:
        #     filtered_tasks = [task for task in filtered_tasks if task.current_status() in status]

    context = {
            'task_filter_form': task_filter_form,
            'filtered_tasks': filtered_tasks,
            }
    
    return render(request, 'status_update_page.html', context)



def status_update(request, task_id):
    # For Section 1
    task = get_object_or_404(Task, id=task_id)
    work_request = task.work_request

    # For Section 2
    status_history = StateDuration.objects.filter(task=task).order_by('-start_time')

    if 'update_end_time' in request.POST:
        status_id = request.POST.get('status.id')
        end_date = request.POST.get('end_date')
        end_time = request.POST.get('end_time')

        #Combine Date and Time from Picker
        end_date_time_str = f"{end_date} {end_time}"
        end_date_time_obj = datetime.strptime(end_date_time_str, '%Y-%m-%d %H:%M')

        status_instance = get_object_or_404(StateDuration, id=status_id)
        status_instance.end_time = end_date_time_obj
        status_instance.save()

        return redirect('status_update', task_id)


    # For Section 3
    if request.method == 'POST':
        form = StatusUpdateForm(request.POST)
        if form.is_valid():

            # Collect Start Date and Start Time from POST data
            start_date_str = request.POST.get('start_time_date')
            start_time_str = request.POST.get('start_time_time')

            # Combine date and time into a datetime object
            start_time_combined_str = f"{start_date_str} {start_time_str}"
            start_time_combined = datetime.strptime(start_time_combined_str, '%Y-%m-%d %H:%M')

            # Save operation and Logic
            new_state_duration = form.save(commit=False)
            new_state_duration.task = task
            new_state_duration.start_time = start_time_combined
            new_state_duration.save()
            form.save_m2m() #For Many to Many Fields like workers
            

            # Update end_time of previous StateDuration entry
            prev_state_duration = StateDuration.objects.filter(task=task).exclude(id=new_state_duration.id).order_by('-start_time').first()
            if prev_state_duration:
                if prev_state_duration.end_time is None:
                    prev_state_duration.end_time = start_time_combined


                # Calculation of normal_duration and overtime_duration

                if prev_state_duration.state == 5:
                    worker_type = prev_state_duration.workers.first().worker_type

                    if worker_type == 'Local':
                        normal_duration , overtime_duration = calculate_duration_for_local(prev_state_duration.start_time, prev_state_duration.end_time)
                    else:
                        normal_duration, overtime_duration = calculate_duration_for_expat(prev_state_duration.start_time, prev_state_duration.end_time)
                    
                else:
                    prev_state_duration.end_time = prev_state_duration.end_time.replace(tzinfo=None)
                    prev_state_duration.start_time = prev_state_duration.start_time.replace(tzinfo=None)
                    
                    normal_duration = prev_state_duration.end_time - prev_state_duration.start_time
                    overtime_duration = timedelta(minutes=0)

                prev_state_duration.normal_duration = normal_duration
                prev_state_duration.overtime_duration = overtime_duration
                prev_state_duration.save() 

            # Update the current_status of the task
            latest_state = StateDuration.objects.filter(task=task).order_by('-start_time').first()
            if latest_state:
                task.current_status = latest_state.state
                task.save()

            return redirect('status_update', task_id=task_id)
    else:
        form = StatusUpdateForm()

    context = {
        'task': task,
        'work_request': work_request,
        'status_history': status_history,
        'form': form,
    }

    return render(request, 'status_update.html', context)




def calculate_workload(request):
    if request.method == 'POST':

        # Filter active machining tasks
        active_machining_tasks = Task.objects.exclude(current_status__in=[6,7]).filter(machining=True)

        # Calculate the current workload
        current_workload = sum(task.assessment_time.total_seconds()/3600 for task in active_machining_tasks if task.assessment_time)

        #Create new CachedCalculation record
        cached_calculation = CachedCalculation.objects.create(
            date = timezone.now().date(),
            machining_workload = current_workload
        )

        return redirect('home')
    


def dashboard_home(request):
    #Loop to count for active work requests (not completed or cancelled)
    active_work_requests_count = 0
    for work_request in WorkRequest.objects.all():
        if work_request.tasks.exclude(current_status__in=[6,7]).exists():
            active_work_requests_count +=1

    #Count of active tasks (not Completed or Cancelled)
    active_tasks = Task.objects.exclude(current_status__in=[6,7])
    active_tasks_count = active_tasks.count()

    #Count of active machining tasks
    active_machining_tasks = Task.objects.filter(machining=True).exclude(current_status__in=[6,7])
    active_machining_tasks_count = active_machining_tasks.count()

    #Count for active non machining tasks
    active_non_machining_tasks = Task.objects.filter(machining=False).exclude(current_status__in=[6,7])
    active_non_machining_tasks_count = active_non_machining_tasks.count()

    
    
    #GRAPH1 Heatmap

    tasks = Task.objects.exclude(current_status__in=[6,7])

    #Data Preparation for DataFrame
    work_types = []
    current_statuses = []
    lead_times = []
    for task in tasks:
        work_types.append(task.get_task_type_display())
        current_statuses.append(task.get_current_status_display())
        lead_time = (datetime.now().date() - task.work_request.date).days
        lead_times.append(lead_time)

    #Create the Dataframe
    df1 = pd.DataFrame({
        'Work Type': work_types,
        'Current Status': current_statuses,
        'Lead Time': lead_times
    })

    grouped_df1 = df1.groupby(['Work Type', 'Current Status']).agg({'Lead Time'  : 'mean'}).reset_index()


    #Create Plotly Heatmap
    fig1 = px.density_heatmap(grouped_df1, x='Work Type', y='Current Status', z='Lead Time', color_continuous_scale='OrRd')
    fig1.update_layout(
        title={
            'text': 'Avg. Lead Time (days) by Current Status',
            'x':0.5,
            'xanchor': 'center'
        },
        coloraxis_colorbar_title='Avg. Lead Time',
        )
    fig1.update_traces(
        hovertemplate="Lead Time: %{z:.1f} days"
    )

    #Convert to HTML
    plot1_html = pyo.plot(fig1, output_type='div')


    #GRAPH2 Stacked Bar Chart

    task2 = Task.objects.exclude(current_status__in=[6,7])

    statuses = []
    urgencies = []
    assessment_times = []

    for task in task2:
        statuses.append(task.get_current_status_display())
        urgencies.append(task.get_urgency_display())
        assessment_times.append(task.assessment_time.total_seconds()/3600 if task.assessment_time else 0)
    
    #Create the DataFrame
    df2 = pd.DataFrame({
        'Status': statuses,
        'Urgency': urgencies,
        'Assessment Time': assessment_times
    })

    #Group and Aggregate
    grouped_df2 = df2.groupby(['Status','Urgency']).agg({'Assessment Time': 'sum'}).reset_index()

    #Create Plotly Stacked Bar Chart
    fig2 = px.bar(grouped_df2, x='Status', y='Assessment Time', color='Urgency', color_discrete_sequence= px.colors.sequential.RdBu, text_auto=True)

    fig2.update_layout(
        title={
            'text':'Workload (Hrs) by Status and Urgency',
            'x': 0.5,
            'xanchor': 'center',                                                                                                            
        })
    
    fig2.update_traces(
        hovertemplate="%{y}",
    )

    #convert to HTML
    plot2_html = pyo.plot(fig2, output_type='div')



    #GRAPH3 Sunburst Assessment_time by unit and Urgency

    task3 = Task.objects.exclude(current_status__in=[6,7])

    units = []
    urgencies = []
    assessment_times = []

    for task in task3:
        units.append(task.work_request.get_unit_display())
        urgencies.append(task.get_urgency_display())
        assessment_times.append(task.assessment_time.total_seconds()/3600 if task.assessment_time else 0)

    #Converting to DataFrame
    df3 = pd.DataFrame({
        'Unit': units,
        'Urgency': urgencies,
        'Assessment Time': assessment_times
    })

    df3['Root'] = 'Total Hrs'


    grouped_df3= df3.groupby(['Root','Unit','Urgency']).agg({'Assessment Time': 'sum'}).reset_index()

    fig3 = px.sunburst(grouped_df3, 
                       path=['Root', 'Unit','Urgency'],
                       values='Assessment Time',
                       color_discrete_sequence= px.colors.sequential.RdBu,
                       maxdepth=2)
    fig3.update_layout(title=dict(
        text='Workload (Hrs) by Unit and Urgency',
        x=0.5,
        xanchor='center'))
    fig3.update_traces(textinfo='label+value',
                       hovertemplate = None,
                       hoverinfo = "skip")

    #Converting to HTML
    plot3_html = pyo.plot(fig3, output_type='div')


    #GRAPH4 Sunburst of total tasks by Urgency and Unit

    task4 = Task.objects.exclude(current_status__in=[6,7])

    statuses =[]
    urgencies = []
    units = []

    for task in task4:
        statuses.append(task.get_current_status_display())
        urgencies.append(task.get_urgency_display())
        units.append(task.work_request.get_unit_display())

    #Create the Dataframe
    df4 = pd.DataFrame({
        'Status': statuses,
        'Urgency': urgencies,
        'Unit': units
    })

    df4['Root'] = 'Total Tasks'

    grouped_df4 = df4.groupby(['Root', 'Status','Urgency','Unit']).size().reset_index(name='Count')

    fig4 = px.sunburst(
        grouped_df4,
        path=['Root', 'Status', 'Urgency', 'Unit'],
        values='Count',
        color_discrete_sequence= px.colors.sequential.RdBu_r,
        maxdepth=2)
    
    fig4.update_layout(title=dict(
    text='Tasks by Status, Urgency & Unit',
    x=0.5,
    xanchor='center'))
    
    fig4.update_traces(textinfo='label+value',
                       hovertemplate = None,
                       hoverinfo = "skip")

    #Converting to HTML
    plot4_html = pyo.plot(fig4, output_type='div')


    # Section 3 
    # Planning Table

    machining_for_today = Task.objects.filter(machining = True , current_status__in=[2,5])
    non_machining_for_today = Task.objects.filter(machining = False, current_status__in=[2,5])

    for task in machining_for_today:
        delta_time = datetime.now().date() - task.work_request.date
        task.lead_time = f"{delta_time.days} days {delta_time.seconds//3600} hours"

        latest_state = task.stateduration_set.order_by('-start_time').first()
        if latest_state:
            task.worker_allocated = ", ".join([str(worker) for worker in latest_state.workers.all()])



    for task in non_machining_for_today:
        delta_time = datetime.now().date() - task.work_request.date
        task.lead_time = f"{delta_time.days} days {delta_time.seconds//3600} hours"

        latest_state = task.stateduration_set.order_by('-start_time').first()
        if latest_state:
            task.worker_allocated = ", ".join([str(worker) for worker in latest_state.workers.all()])

    

    # Section 4 
    #Completed Tasks

    today = timezone.now().date()

    #Check if today is monday to include saturday and sunday
    if today.weekday()==0:
        saturday = today - timedelta(days=2)
        sunday = today - timedelta(days=1)
        completed_tasks =  Task.objects.filter(stateduration__state=6, stateduration__start_time__date__range=[saturday,sunday]).distinct().order_by('-stateduration__start_time')

    else:
        yesterday = today - timedelta(days=1)
        completed_tasks = Task.objects.filter(stateduration__state=6, stateduration__start_time__date= yesterday).distinct().order_by('-stateduration__start_time')


    # Calculations for Completed Machining Tasks
    completed_machining_tasks = completed_tasks.filter(machining=True)
    for task in completed_machining_tasks:

        # Calculation of Cumm Normal Hrs and Overtime Hrs
        durations_in_progress = StateDuration.objects.filter(task=task, state=5)
        normal_hrs_sum = durations_in_progress.aggregate(total=Sum('normal_duration'))['total'] or timedelta()
        task.normal_hrs_sum = normal_hrs_sum
        overtime_hrs_sum = durations_in_progress.aggregate(total=Sum('overtime_duration'))['total'] or timedelta()
        task.overtime_hrs_sum = overtime_hrs_sum

        # Calculation of lead time 
        completion_state = task.stateduration_set.filter(state=6).order_by('-start_time').first()
        if completion_state:
            work_request_datetime = make_aware(datetime.combine(task.work_request.date, time.min))
            delta_time = completion_state.start_time - work_request_datetime
            task.lead_time = f"{delta_time.days} days {delta_time.seconds//3600} hrs"

        # Calculations regarding latest allocated Technician
        latest_wip = task.stateduration_set.filter(state=5).order_by('-end_time').first()
        if latest_wip:
            task.worker_allocated = ", ".join([str(worker) for worker in latest_wip.workers.all()])
        

    # Calculations for Completed non machining tasks
    completed_non_machining_tasks = completed_tasks.filter(machining=False)
    for task in completed_non_machining_tasks:

        #Calculation of Cumm Normal Hrs and Overtime Hrs
        durations_in_progress = StateDuration.objects.filter(task=task, state=5)
        normal_hrs_sum = durations_in_progress.aggregate(total=Sum('normal_duration'))['total'] or timedelta()
        task.normal_hrs_sum = normal_hrs_sum
        overtime_hrs_sum = durations_in_progress.aggregate(total=Sum('overtime_duration'))['total'] or timedelta()
        task.overtime_hrs_sum = overtime_hrs_sum

        # Calculation of lead time 
        completion_state = task.stateduration_set.filter(state=6).order_by('-start_time').first()
        if completion_state:
            work_request_datetime = make_aware(datetime.combine(task.work_request.date, time.min))
            delta_time = completion_state.start_time - work_request_datetime
            task.lead_time = f"{delta_time.days} days {delta_time.seconds//3600} hrs"

        # Calculations regarding latest allocated Technician
        latest_wip = task.stateduration_set.filter(state=5).order_by('-end_time').first()
        if latest_wip:
            task.worker_allocated = ", ".join([str(worker) for worker in latest_wip.workers.all()])

        
    # Calculation of Machining Workload Trend
    
    total_assessment_time = active_machining_tasks.aggregate(total=Sum('assessment_hours'))['total'] or 0
    previous_machining_workload = CachedCalculation.objects.latest('id').machining_workload
    machining_workload_comparison = total_assessment_time - previous_machining_workload



    context = {
        'active_work_requests_count' : active_work_requests_count,
        'active_tasks_count' : active_tasks_count,
        'active_machining_tasks_count' : active_machining_tasks_count,
        'active_non_machining_tasks_count' : active_non_machining_tasks_count,
        'plot1' : plot1_html,
        'plot2' : plot2_html,
        'plot3' : plot3_html,
        'plot4' : plot4_html,
        'machining_for_today' : machining_for_today,
        'non_machining_for_today' : non_machining_for_today,
        'completed_machining_tasks' : completed_machining_tasks,
        'completed_non_machining_tasks' : completed_non_machining_tasks,
        'machining_workload_comparison' : machining_workload_comparison,
    }

    return render(request, 'dashboard_home.html', context)

def basic_home(request):
    return render(request, 'basic_home.html')







        

    















    
    





