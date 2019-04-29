from datetime import datetime as dt

# TODO: Sometimes there is no/low voltage on a phase. This should be ignored when calculating average

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


def find_meter_voltage(voltages):
    """
    Tries to guess what voltage meter supposed to measure based on all three phases voltages
    :param voltages: [phase1, phase2, phase3]
    :return: one of [230, 6000, 10000, 11000, 12000, 20000, 30000, 110000, 222000]
    """
    assert isinstance(voltages, list), "Received voltages \"%s\" which is not a list" % voltages
    medium_voltage = 0
    for voltage in voltages:
        medium_voltage += voltage
    medium_voltage = medium_voltage / len(voltages)

    if medium_voltage < 500:
        return 230
    elif 1000 < medium_voltage < 8000:
        return 6000
    elif 8000 <= medium_voltage < 10500:
        return 10000
    elif 11000 <= medium_voltage < 15000:
        return 12000
    elif 15000 <= medium_voltage < 25000:
        return 20000
    elif 25000 <= medium_voltage < 45000:
        return 30000
    elif 45000 <= medium_voltage < 160000:
        return 110000
    elif medium_voltage >= 160000:
        return 222000

