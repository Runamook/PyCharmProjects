import json
try:
    from .Helpers.create_logger import create_logger
except ImportError:
    from Helpers.create_logger import create_logger
try:
    from .emhmeter import *
except ModuleNotFoundError:
    from emhmeter import *
from time import sleep
import datetime


class CRMtoRedis:

    url = "http://10.11.30.97:5000/api/MeteringPointWithSchedule"
    generic_log = "/var/log/eg/crm_to_redis.log"
    file_cache = "/tmp/_crm_to_redis_cache_1wed.txt"

    def __init__(self, llevel):
        self.logger = create_logger(loglevel=llevel, instance_name="CRMtoRedis", log_filename=self.generic_log)

    def transform_meter(self, meter):
        """
        Transforms data to the format expected by emhmeter.py
        More or less

        API:
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

       Expected:
           {
            "meterNumber": "06205102",
            "Manufacturer": "EMH",
            "ip": "10.124.2.111",
            "voltageRatio": 200,
            "currentRatio": 10,
            "totalFactor": 210
                      "schedule":{
             "p01":"3600",
             "p200":"3600",
             "p211":"3600",
             "table1":"3600",
             "table2":"3600",
             "table3":"3600",
             "table4":"3600",
             "time":"3600"
          }
        }

        """
        try:
            location = meter["meteringPointLabel"]
            ip = meter["ip"]
            name = meter["installedMeter"]["name"]
            manufacturer = meter["installedMeter"]["manufacturer"]
            transform_curent = meter["transformerFactors"]["current"]
            transform_voltage = meter["transformerFactors"]["voltage"]
            schedule = meter["schedule"]
        except KeyError:
            self.logger.error(f"Some key is missing in {meter}")
            return None

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

    @staticmethod
    def get_cache():
        with open(CRMtoRedis.file_cache, 'r') as f:
            return f.read()

    @staticmethod
    def update_cahce(value):
        with open(CRMtoRedis.file_cache, 'w') as f:
            f.write(value)
        return

    def get_crm_data(self):
        """
        Parses data returned by API
        Transforms data to the format expected by emhmeter.py
        """
        try:
            results = requests.get(self.url, timeout=10).json()
            self.update_cahce(json.dumps(results))
        except Exception as e:
            self.logger.error(f"{e} error when getting data from {self.url}")
            self.logger.warning(f"Reading cached data")
            results = json.loads(self.get_cache())

        meter_list = []
        for meter in results:
            self.logger.debug(f"Found meter {meter}")
            new_meter = self.transform_meter(meter)
            if new_meter:
                self.logger.debug(f"Transform to {new_meter}")
                meter_list.append(new_meter)

        return json.dumps(meter_list)

    def push_to_redis(self, data):
        try:
            r = Redis(charset="utf-8", decode_responses=True)
            r.set("crm_response", data)
            self.logger.info(f"Pushed data to redis")
        except Exception as e:
            self.logger.error(f"{e} error when connecting to Redis")
            raise e

    def run(self):
        d = self.get_crm_data()
        self.push_to_redis(d)


class RedistoJob:

    log_dir = "/var/log/eg"
    job_functions = {
        "p01": rq_create_p01_jobs,
        "p200": rq_create_logbook_jobs,
        "p211": None,                           # Collected with p200, additional job not required
        "table1": rq_create_table1_jobs,
        "table2": None,
        "table3": None,
        "table4": rq_create_table4_jobs,
        "time": rq_create_time_jobs
    }
    not_implemented = ["p211", "table2", "table3"]

    def __init__(self, llevel, istest=False):
        self.logger = create_logger(loglevel=llevel,
                                    instance_name="RedisToJob",
                                    log_filename=CRMtoRedis.generic_log
                                    )
        self.test = istest
        try:
            self.redis_conn = Redis(charset="utf-8", decode_responses=True)
        except Exception as e:
            self.logger.error(f"{e} error when connecting to Redis")
            raise e

    def get_from_redis(self):
        """
        Tries to get data from redis by "crm_response" key
        Converts JSON string to python object

        :returns [{meter obj}, {meter obj}, {meter obj}]
        """
        data = json.loads(self.redis_conn.get("crm_response"))

        if not data:
            self.logger.error("Empty response from Redis")
            raise ValueError
        self.logger.debug(data)
        return data

    def create_jobs(self, meter):
        """
        Create redis jobs according to schedule in meter object
        """
        self.logger.debug(f"Meter {meter['meterNumber']}, jobs {meter['schedule']}")
        for job_type in meter["schedule"].keys():
            self.check_for_job(meter, job_type)

    def check_for_job(self, meter, job_type):
        """
        Check if a jobs can be executed - the time in schedule has passed
        :param meter - meter dict
        :param job_type - string from schedule
        """
        push = False
        meter_number = meter["meterNumber"]

        if job_type == "table1":
            if not self.requeue_jobs(job_type, meter_number):
                # If the job was not requeued and it's not running
                if datetime.datetime.now().day == 1:
                    # Table1 should only be pushed at 1st day of month
                    push = True
                else:
                    self.logger.debug(f"Meter {meter_number} skipping table1, not 1st day of month")

        # Skip all, except for P01 for Metcom - they are not responding
        elif meter['Manufacturer'].lower() == 'metcom' and job_type != 'p01':
            push = False

        else:
            interval = meter["schedule"][job_type]
            # Search for job in redis
            job_time = self.redis_conn.get(f"CRM:{meter_number}:{job_type}")
            if job_time:
                # Such job was pushed to redis, should check time
                if self.check_time(job_time, interval):
                    push = True
            else:
                # Job was never pushed to redis
                push = True

        if push:
            self.push_job(meter, job_type)
        else:
            self.logger.debug(f"Meter {meter_number}, skipping job {job_type}")

    def check_time(self, job_time, interval):
        """
        Checks if the interval has passed since job_time
        :param job_time: epoch received from redis
        :param interval: interval from API (now 24 Hours, will be epoch)
        :return: boolean
        """
        now = datetime.datetime.utcnow()
        # self.logger.debug(f"Job time {job_time}")
        job_dt = datetime.datetime.fromtimestamp(int(job_time))
        interval = self.normalize_interval(interval)
        delta = datetime.timedelta(seconds=interval)
        return (now - delta) > job_dt

    def normalize_interval(self, interval):
        """
        Fix interval so in is the number of seconds
        :param interval: API response,
        :return: interval in seconds
        """
        if interval == "24 Hours":
            interval = "86400"
        return int(interval)

    def push_job(self, meter, job_type):
        """
        Push job to redis queue
        :param meter: meter dict
        :param job_type: string job from API schedule
        """
        meter_number = meter["meterNumber"]
        epoch = datetime.datetime.strftime(datetime.datetime.utcnow(), "%s")
        # Skip jobs that we don't want to do
        if job_type not in self.not_implemented:
            meter_list = [meter]                            # rq_create... expects list of meters
            job_function = self.job_functions[job_type]     # Determine job push function
            try:
                job_function(meter_list, test=self.test)                        # Push job
                self.redis_conn.set(f"CRM:{meter_number}:{job_type}", epoch)
            except Exception as e:
                self.logger.error(f"Meter {meter_number} error {e} while pushing job")
                raise e
            self.logger.debug(f"Meter {meter_number} pushed {job_type} job")

    def requeue_jobs(self, q_name, meter_number):
        if self.test:
            q = Queue(name=f"test-{q_name}", connection=Redis())
        else:
            q = Queue(name=q_name, connection=Redis())

        running_jobs, failed_jobs = get_job_meta(q)
        self.logger.debug(f"Meter {meter_number} running jobs {running_jobs.get(meter_number)}, failed jobs {failed_jobs.get(meter_number)}")
        if meter_number in failed_jobs:
            # Meter query is failed, shall not be queued, but shall be requeued
            job_id = failed_jobs[meter_number]["job_id"]
            timestamp = failed_jobs[meter_number]["timestamp"]
            q.failed_job_registry.requeue(job_id)
            self.logger.debug(f"Meter {meter_number} requeued failed table1 job {job_id} at {timestamp}")
            return True
        elif meter_number in running_jobs:
            logger.debug(f"Meter {meter_number} query for {q_name} is running")
            # Query is running, no need to requeue or queue
            return True
        return False

    def run(self):
        # Get data from redis, should be a list of dicts
        meters = self.get_from_redis()
        for meter in meters:
            self.create_jobs(meter)


if __name__ == "__main__":
    for _ in range(5):
        start = datetime.datetime.now()
        a = CRMtoRedis(llevel="DEBUG")
        a.run()
        test = False
        b = RedistoJob(llevel="DEBUG", istest=test)
        b.run()
        time_spent = int((datetime.datetime.now() - start).seconds)
        if time_spent >= 10:
            sleep(0)
        else:
            sleep(10 - time_spent)

