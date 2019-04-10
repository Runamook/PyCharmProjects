from datetime import datetime as dt

Numeric_Metrics = ["WirkleistungP1", "WirkleistungP2", "WirkleistungP3", "WirkleistungGesamt",
                   "BlindleistungP1", "BlindleistungP2", "BlindleistungP3", "BlindleistungGesamt",
                   "ScheinleistungP1", "ScheinleistungP2", "ScheinleistungP3", "ScheinleistungGesamt",
                   "StromP1", "StromP2", "StromP3",
                   "SpannungP1", "SpannungP2", "SpannungP3",
                   "LeistungsfaktorP1", "LeistungsfaktorP2", "LeistungsfaktorP3", "LeistungsfaktorGesamt",
                   "Frequenz",
                   "EinAusgangsSteuerSignal", "InternalSteuerSignal",
                   "PhasenAusfalleCounterGesamt",
                   "PhasenAusfalleCounterP1", "PhasenAusfalleCounterP2", "PhasenAusfalleCounterP3",
                   "DCFLastSync", "PhaseInformation", "InstallationsKontrol"
                   ]


def make_dates():
    day = str(dt.now().day)
    if len(day) > 1:
        pass
    else:
        day = "0" + day

    month = str(dt.now().month)
    if len(month) > 1:
        pass
    else:
        month = "0" + month

    year = str(dt.now().year)

    return "%s.%s.%s" % (day, month, year)


def get_metric_time(metric):
    date = str(metric["Date"])           # "20190408"
    hour = str(metric["Hour"])           # "1"
    minute = str(metric["Minute"])       # "15"

    if len(hour) > 1:
        pass
    else:
        hour = "0" + hour           # "00"
    if len(minute) > 1:
        pass
    else:
        minute = "0" + minute

    epoch = dt.strptime(date + hour + minute, "%Y%m%d%H%M").strftime("%s")

    return int(epoch)
