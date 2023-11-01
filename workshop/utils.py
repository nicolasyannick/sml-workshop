from datetime import  timedelta, time


def calculate_duration_for_local(start_time, end_time):
    day_of_week = start_time.weekday()

    normal_start, normal_end = time(8,0), time(17,0)
    if day_of_week == 5:
        normal_start, normal_end = time(8,0), time(12,0)
    elif day_of_week == 6:
        normal_start, normal_end = time(0,0), time(0,0)

    return calculate_duration(start_time, end_time, normal_start, normal_end)

        

def calculate_duration_for_expat(start_time, end_time):
    day_of_week = start_time.weekday()

    normal_start, normal_end = time(7,30), time(17,15)
    if day_of_week == 5 or day_of_week == 6:
        normal_start, normal_end = time(0,0), time(0,0)

    return calculate_duration(start_time, end_time, normal_start, normal_end)



def calculate_duration(start_time, end_time,normal_start, normal_end):
    normal_duration = timedelta()
    overtime_duration = timedelta()
    
    start_time_time = start_time.time()
    end_time_time = end_time.time()

    end_time = end_time.replace(tzinfo=None)
    start_time = start_time.replace(tzinfo=None)



    if start_time_time >= normal_start and end_time_time <= normal_end:
        normal_duration = end_time - start_time
    elif start_time_time < normal_start and end_time_time <= normal_end:
        normal_duration = end_time - start_time.replace(hour=normal_start.hour, minute=normal_start.minute)
        overtime_duration = start_time.replace(hour=normal_start.hour, minute=normal_start.minute) - start_time    
    elif start_time_time >= normal_start and end_time_time > normal_end:
        normal_duration = start_time.replace(hour=normal_end.hour, minute=normal_end.minute) - start_time
        overtime_duration = end_time - start_time.replace(hour=normal_end.hour, minute=normal_end.minute)    
    else:
        normal_duration = start_time.replace(hour=normal_end.hour, minute=normal_end.minute) - start_time.replace(hour=normal_start.hour, minute=normal_start.minute)
        overtime_duration = (end_time - start_time.replace(hour=normal_end.hour, minute=normal_end.minute)) + (start_time.replace(hour=normal_start.hour, minute=normal_start.minute) - start_time)
    
    return normal_duration, overtime_duration



