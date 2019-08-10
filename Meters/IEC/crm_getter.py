import requests
from redis import Redis
import json
import sqlalchemy

"""
   { 
      "installedCommunicationModule":"20001070",
      "customer":"Plan_E GmbH",
      "dgo":"E.DIS AG",
      "ip":"10.124.2.34",
      "meteringPointGuid":"9337106a-9949-e911-810f-00155d15ce15",
      "meteringPointLabel":"DE00100016831S0000000000001057725",
      "operator":"Plan_E GmbH",
      "installedRouter":"NONE",
      "shortName":"PAR-1900226-03 Rheinsberg",
      "installedSim":"8934075100252491857",
      "installedMeter":{ 
         "name":"10001802",
         "type":"MCS301-CW31B-2EMIS-024100",
         "manufacturer":"Metcom"
      },
      "transformerFactors":{ 
         "current":150,
         "voltage":5
      },
      "schedule":{ 
         "p01":"24 Hours",
         "p200":"24 Hours",
         "p211":"24 Hours",
         "table1":"24 Hours",
         "table2":"24 Hours",
         "table3":"24 Hours",
         "table4":"24 Hours",
         "time":"24 Hours"
      }
   }
   
   
       {
        "meterNumber": "06205102",
        "Manufacturer": "",
        "ip": "10.124.2.111",
        "InstallationDate": "2018-10-10T10:00:00",
        "IsActive": True,
        "voltageRatio": 200,
        "currentRatio": 10,
        "totalFactor": 210
    }
"""


def transform_meter(meter):
    location = meter["meteringPointLabel"]
    ip = meter["ip"]
    name = meter["installedMeter"]["name"]
    manufacturer = meter["installedMeter"]["manufacturer"]
    transform_curent = meter["transformerFactors"]["current"]
    transform_voltage = meter["transformerFactors"]["voltage"]
    schedule = meter["schedule"]

    result = dict()
    result["meterNumber"] = name
    result["location"] = location
    result["Manufacturer"] = manufacturer
    result["ip"] = ip
    result["voltageRatio"] = transform_voltage
    result["currentRatio"] = transform_curent
    result["totalFactor"] = str(int(transform_voltage) * int(transform_voltage))
    result["schedule"] = schedule

    return result


def get_crm_data():
    url = "http://10.11.30.97:5000/api/MeteringPointWithSchedule"
    results = requests.get(url)

    meter_list = []

    for meter in results.json():
        new_meter = transform_meter(meter)
        meter_list.append(new_meter)

    return json.dumps(meter_list)


def push_to_redis(data):

    r = Redis()
    r.set("crm_response", data)


def get_from_redis():

    r = Redis()
    data = json.loads(r.get("crm_response"))
    for meter in data:
        print(meter)


if __name__ == "__main__":
    d = get_crm_data()
    push_to_redis(d)
    get_from_redis()
