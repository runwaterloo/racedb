from datetime import timedelta

def truncate_time(time):
    try:
        int(time)
    except:
        trunc_time = time - timedelta(microseconds=time.microseconds)
    else:
        ustime = timedelta(microseconds=time)
        trunc_time = ustime - timedelta(microseconds=ustime.microseconds)
    return trunc_time

