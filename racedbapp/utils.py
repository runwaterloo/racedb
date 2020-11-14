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

    if raw_place < 990000:
        place = raw_place
    elif raw_place >= 990000 and raw_place < 991000:
        place = "DQ"
    elif raw_place >= 991000 and raw_place < 992000:
        place = "DNF"
    else:
        place = "DNS"
    return place
