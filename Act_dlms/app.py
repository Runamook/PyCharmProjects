#!/opt/meter_iec/venv/bin/python
from .emhmeter import rq_create_table1_jobs, rq_create_p01_jobs, rq_create_table4_jobs, logger
import time
import sys
import argparse
try:
    from Act_dlms.Helpers.list_of_meters import list_of_meters_2 as list_of_meters
except ImportError:
    from Helpers.list_of_meters import list_of_meters_2 as list_of_meters


def main(dataset, frequent, llevel, test):
    logger.setLevel(llevel)
    logger.info(f"Starting app with dataset: {dataset}, frequent: {frequent}, test: {test}")

    if dataset == "t1":
        job = rq_create_table1_jobs
    elif dataset == "t4":
        job = rq_create_table4_jobs
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


if __name__ == "__main__":
    optparser = argparse.ArgumentParser(description="Push jobs into Redis queue. Request meter data using IEC protocol")
    required = optparser.add_argument_group('Data set')
    optparser.add_argument("--llevel", type=str, help="Loglevel - one of INFO, DEBUG, WARN, CRITICAL. Default: INFO")
    optparser.add_argument("--frequent", type=str, help="If True - pushes 6 jobs in a minute. Default: False")
    optparser.add_argument("--test", type=str, help="Changes queue names. Default: False")
    required.add_argument("--dataset", type=str, help="p01, t1, t4", required=True)

    args = optparser.parse_args()

    valid_datasets = ["p01", "t1", "t4"]
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

    main(dataset, frequent, llevel, test)
