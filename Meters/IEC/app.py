#!/opt/meter_iec/venv/bin/python
try:
    from .emhmeter import rq_create_table1_jobs, rq_create_p01_jobs, rq_create_table4_jobs, rq_create_logbook_jobs, logger, get_job_meta
except ImportError:
    from emhmeter import rq_create_table1_jobs, rq_create_p01_jobs, rq_create_table4_jobs, logger, rq_create_logbook_jobs, get_job_meta
import time
import sys
import argparse
from redis import Redis
from rq import Queue
try:
    from .Helpers.list_of_meters import list_of_meters_2 as list_of_meters
except ImportError:
    from Helpers.list_of_meters import list_of_meters_2 as list_of_meters


def main(dataset, frequent, llevel, test):
    logger.setLevel(llevel)
    logger.info(f"Starting app with dataset: {dataset}, frequent: {frequent}, test: {test}")

    if dataset == "t1":
        job = rq_create_table1_jobs
    elif dataset == "t4":
        job = rq_create_table4_jobs
    elif dataset == "logbook":
        job = rq_create_logbook_jobs
    else:
        job = rq_create_p01_jobs

    if frequent == "True":
        for _ in range(5):
            job(list_of_meters, test)
            time.sleep(10)
        job(list_of_meters, test)
    elif frequent == "False":
        job(list_of_meters, test)

    return


def requeue_jobs(q_name, test):
    if test:
        q = Queue(name=f"test-{q_name}", connection=Redis())
    else:
        q = Queue(name=q_name, connection=Redis())
    logger.info("Connected to redis")

    running_jobs, failed_jobs = get_job_meta(q)
    print(running_jobs, failed_jobs)
    for meter in failed_jobs:
        job_id = failed_jobs[meter]["job_id"]
        q.failed_job_registry.requeue(job_id)
        logger.debug(f"Meter {meter} requeued failed table1 job {job_id}")


if __name__ == "__main__":
    optparser = argparse.ArgumentParser(description="Push jobs into Redis queue. Request meter data using IEC protocol")
    required = optparser.add_argument_group('Data set')
    optparser.add_argument("--llevel", type=str, help="Loglevel - one of INFO, DEBUG, WARN, CRITICAL. Default: INFO")
    optparser.add_argument("--frequent", type=str, help="If True - pushes 6 jobs in a minute. Default: False")
    optparser.add_argument("--test", type=str, help="Changes queue names. Default: False")
    optparser.add_argument("--requeue", type=str, help="Requeue failed jobs, only for Table1")
    required.add_argument("--dataset", type=str, help="p01, t1, t4, logbook", required=True)

    args = optparser.parse_args()

    valid_datasets = ["p01", "t1", "t4", "logbook"]
    valid_loglevels = ["DEBUG", "INFO", "WARN", "CRITICAL"]

    if args.dataset in valid_datasets:
        dataset = args.dataset
    else:
        print("Unknown operation %s" % args.dataset)
        sys.exit(1)

    if not args.frequent:
        frequent = "False"
    else:
        frequent = args.frequent

    if not args.llevel or args.llevel not in valid_loglevels:
        llevel = "INFO"
    else:
        llevel = args.llevel

    if args.test == "True":
        test = True
    else:
        test = False

    if args.requeue:
        if dataset != "t1":
            print("Requeue only valid for Table1")
            sys.exit(1)
        else:
            requeue_jobs("table1", test)
    else:
        main(dataset, frequent, llevel, test)

