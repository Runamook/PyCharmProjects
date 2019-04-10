from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import StatementError, IntegrityError
import csv
import whois
import time
import re
from datetime import datetime as dtime
import datetime
import argparse

try:
    from Whois_scrapper_compose.helper_functions import helper_functions, create_logger, synonyms
except ImportError:
    from helper_functions import helper_functions, create_logger, synonyms
from multiprocessing.dummy import Pool
from time import sleep


class Scrapper:
    def __init__(self,
                 input_name,
                 log_filename,
                 db_filename,
                 apikey=None,
                 input_data_query="None",
                 use_proxy="False",
                 loglevel="INFO",
                 threads=2):

        self.input_name = input_name
        self.db_filename = db_filename

        # Write metadata to sqlite DB
        self.meta_db_filename = "sqlite:///whois_scrapper_meta.db"
        # Lists of synonyms
        self.synonyms = synonyms.Synonyms()
        # Logging config
        self.logger = create_logger.create_logger(log_filename, __name__, loglevel)
        self.logger.info("Starting with parameters \
        \n Input: %s\n Log: %s\n DB: %s\n Metadata: %s\n Input Query %s\n Proxy %s\n" % (input_name, log_filename, db_filename, self.meta_db_filename, input_data_query, use_proxy))

        if input_data_query == "None":
            input_data_query = None
        if use_proxy == "False":
            use_proxy = False
        elif use_proxy == "True":
            use_proxy = True
        else:
            self.logger.error("Proxy can be \"True\" or \"False\"")
            exit(1)

        self.results = None

        self.apikey = apikey
        self.use_proxy = use_proxy

        self.refused_counter = 0
        self.pause_times = {  # Refuses : Seconds
            10: 20,  # 10 is mandatory
            80: 60,
            150: 120,
            280: "restart"
        }
        """
        self.pause_times = {    # Refuses : Seconds
            10: 20,             # 10 is mandatory
            40: 60,
            80: 120,
            90: 180,
            99: "restart"
        }
        """

        pool_size = threads              # Multi-thread flows
        bucket_size = 300           # Domains processed at once
        self.buckets_processed = 0
        self.logger.info("Created Scrapper object\tPool size = %s\tBucket size = %s" % (pool_size, bucket_size))
        # Create tables
        helper_functions.create_tables(self.db_filename, self.meta_db_filename, self.logger)

        # Multi thread pool
        self.bucket_size = bucket_size
        self.pool = Pool(pool_size)

        if self.use_proxy:
            socks_proxy = helper_functions.change_proxy(self.apikey)
            self.logger.warning("Proxy set, new proxy %s" % socks_proxy)

        if input_data_query is None:
            self.input_data_query = "SELECT domain FROM source_data \
            LEFT JOIN whoistable ON source_data.\"domain\" = whoistable.domain_name \
            WHERE whoistable.domain_name IS NULL \
            LIMIT 20000;"
        else:
            self.input_data_query = input_data_query

        if self.input_name.endswith("csv"):
            self.logger.info("Using CSV input")
            self.domains = self.parse_input()
        else:
            self.logger.info("Using database input")
            self.domains = self.get_input_from_db()

    def parse_input(self):
        """
        Parses CSV file and returns list of domains
        [domainA,domainB,domainC,...]
        """
        result = []
        start_time = time.time()
        with open(self.input_name, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if "." in row[0]:
                    result.append(row[0])
        delta = str(time.time() - start_time)
        self.logger.info("Parsed input in %s seconds, %s domains found" % (delta, len(result)))
        return result

    def get_input_from_db(self):
        """
        :return: [domainA, domainB, domainC,...]
        """
        result = []
        start_time = time.time()
        conn = create_engine(self.db_filename).connect()
        try:
            input_data = conn.execute(self.input_data_query).fetchall()
            for domain_name in input_data:
                result.append(domain_name[0])
        finally:
            conn.close()
        delta = str(time.time() - start_time)
        self.logger.info("Parsed input in %s seconds, %s domains found" % (delta, len(result)))
        return result

    def log_result(self, result):
        """
        In: (domain_name, result)
        """
        if result[1] == "NotExistent":  # Result value
            self.logger.warning("%s --- Not Found" % result[0])
        elif result[1] == "Refused":
            self.logger.warning("%s --- Refused" % result[0])
            self.refused_counter += 1
        elif result[1] == "Timeout":
            self.logger.warning("%s --- Timeout" % result[0])
            self.refused_counter += 0.5
        elif isinstance(result[1], whois.parser.WhoisEntry):
            self.logger.debug("%s --- Found" % result[0])

        else:
            self.logger.error("Something goes wrong %s --- %s" % (result[0], result[1]))

        return

    def bucketize(self):
        """Iterate over [domains] and create list of lists, sized to the bucket_size"""
        self.logger.info("Started bucketizer")
        result = []
        for i in range(len(self.domains)//self.bucket_size):

            result.append(self.domains[:self.bucket_size])
            self.domains = self.domains[self.bucket_size:]
        result.append(self.domains)

        self.domains = result
        self.logger.info("%s buckets found, each %s" % (len(result), self.bucket_size))
        return

    def check_bucket(self, bucket):
        """Checks if domain names in bucket were already processed"""
        # eng = create_engine(self.db_filename)
        eng = create_engine(self.meta_db_filename)
        meta_conn = eng.connect()

        results = []
        try:
            for domain_name in bucket:
                sql_query = "SELECT result FROM results WHERE domain_name = \'%s\'" % domain_name
                status = meta_conn.execute(sql_query)
                query_result = status.fetchall()

                if len(query_result) == 1:
                    # Already processed
                    if query_result[0][0] in ["Processed", "Refused"]:
                        self.logger.debug("%s already processed, skipping" % domain_name)
                        continue
                    elif query_result[0][0] in ["Timeout", "Refused"]:
                        self.logger.debug("%s was tried but failed, retrying" % domain_name)
                        results.append(domain_name)
                elif len(query_result) == 0:
                    # Not yet processed
                    self.logger.debug("%s not yet processed, will put into queue" % domain_name)
                    results.append(domain_name)
        finally:
            meta_conn.close()

        self.logger.info("Bucket shrinked to %s" % len(results))
        return results

    def run(self):

        if not self.use_proxy:
            helper_functions.remove_proxy()

        self.bucketize()

        for bucket in self.domains:
            start_time = time.time()
            self.check_if_pause_needed()
            self.logger.info("Starting a new bucket, %s buckets already processed" % self.buckets_processed)
            bucket = self.check_bucket(bucket)

            self.results = self.pool.map(helper_functions.get_whois, bucket)

            self.write_all_to_db()
            self.buckets_processed += 1
            delta = str(time.time() - start_time)
            self.logger.info("Processed bucket in %s seconds" % delta)

        return

    def check_if_pause_needed(self):
        self.logger.info("Refused counter\t\t\t=\t\t\t[%s]" % self.refused_counter)
        sleep(0.00001)

        if self.refused_counter > 10:
            pause_time = 10     # Default fallback

            # Loop over dict and select pause action/timer
            for counter in self.pause_times:
                if self.refused_counter > counter:
                    pause_time = self.pause_times[counter]

            if pause_time == "restart" and self.use_proxy:
                socks_proxy = helper_functions.change_proxy(self.apikey)
                self.logger.warning("Proxy changed, new proxy %s" % socks_proxy)
                pause_time = 10
            elif pause_time == "restart":
                pause_time = 180

            self.logger.warning("%s refuses, pausing for %s" % (self.refused_counter, pause_time))
            sleep(pause_time)
            self.refused_counter = 0
        else:
            self.logger.info("%s refuses, no pause required" % self.refused_counter)

        return

    def write_all_to_db(self):
        """
        Write all to database
        """
        eng = create_engine(self.db_filename)
        meta_eng = create_engine(self.meta_db_filename)
        conn = eng.connect()
        meta_conn = meta_eng.connect()

        inserts = 0

        try:
            for result in self.results:

                self.log_result(result)
                if result[1] not in ["NotExistent", "Refused", "Timeout"]:
                    assert (isinstance(result[1], whois.parser.WhoisEntry)),\
                        "Not a whois.parser.WhoisEntry object\n%s" % result

                    # Sqlite3 doesn't support ON CONFLICT until version 3.24.0 (2018-06-04)
                    """
                    sql_meta_query = "INSERT INTO results ( \
                        domain_name, \
                        result\
                        ) values (\'%s\', \'Processed\') ON CONFLICT (domain_name) DO UPDATE SET \
                         result = \'Processed\'" % result[0]
                    """
                    sql_meta_query = "INSERT INTO results ( \
                        domain_name, \
                        result\
                        ) values (\'%s\', \'Processed\')" % result[0]
                    sql_meta_query_update = "UPDATE results SET \
                    result=\'Processed\' WHERE domain_name=\'%s\'" % result[0]

                    mark = "ok"
                    inserts += 1
                else:
                    """
                    sql_meta_query = "INSERT INTO results ( \
                        domain_name, \
                        result\
                        ) values (\'%s\', \'%s\') ON CONFLICT (domain_name) DO UPDATE SET \
                         result = \'%s\'" % (result[0], result[1], result[1])
                    """
                    sql_meta_query = "INSERT INTO results ( \
                        domain_name, \
                        result\
                        ) values (\'%s\', \'%s\')" % (result[0], result[1])
                    sql_meta_query_update = "UPDATE results SET \
                    result=\'%s\' WHERE domain_name=\'%s\'" % (result[0], result[1])

                    mark = "continue"

                if mark == "continue":
                    # Not processing further - nothing to insert
                    try:
                        meta_conn.execute(sql_meta_query)
                        self.logger.debug("Inserted metadata for %s into database [skipped]" % result[0])
                    except IntegrityError:
                        meta_conn.execute(sql_meta_query_update)
                        self.logger.debug("Updated metadata for %s in database [skipped]" % result[0])
                    self.logger.debug("Skipping data insertion")
                else:
                    # Insert into data (data)
                    dt = str(datetime.datetime.now())
                    domain_name = helper_functions.sanitize(result[0])

                    name = helper_functions.synonym_finder(result[1], self.synonyms.synonym_name)
                    org = helper_functions.synonym_finder(result[1], self.synonyms.synonym_org)
                    country = helper_functions.synonym_finder(result[1], self.synonyms.synonym_country)
                    city = helper_functions.synonym_finder(result[1], self.synonyms.synonym_city)
                    address = helper_functions.synonym_finder(result[1], self.synonyms.synonym_address)
                    creation_date = helper_functions.synonym_finder(result[1], self.synonyms.synonym_creation_date)
                    if isinstance(creation_date, str) or creation_date is None:
                        creation_date = dtime.strptime('1800-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
                    expiration_date = helper_functions.synonym_finder(result[1], self.synonyms.synonym_expiration_date)
                    if isinstance(expiration_date, str) or expiration_date is None:
                        expiration_date= dtime.strptime('1800-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
                    # Others are processed using helper_functions.sanitize()
                    blob = helper_functions.remove_nonascii(result[1].\
                                                            text.replace("'", '"').\
                                                            replace("\0", " ").\
                                                            strip(" \t\r\n\0").\
                                                            replace("(", "[").\
                                                            replace(")", "]"))
                    blob = re.sub(r'[\x00-\x1f]', r'', blob)

                    # Insert record
                    sql_query = "INSERT INTO whoistable (\
                        dt, \
                        domain_name, \
                        name, \
                        org, \
                        country, \
                        city, \
                        address, \
                        creation_date, \
                        expiration_date, \
                        blob\
                        ) values (\'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\') \
                        ON CONFLICT (domain_name) DO NOTHING" % (
                        dt,
                        domain_name,
                        name,
                        org,
                        country,
                        city,
                        address,
                        creation_date,
                        expiration_date,
                        blob)

                    # https://docs.sqlalchemy.org/en/latest/core/tutorial.html#using-textual-sql
                    try:
                        conn.execute(text(sql_query))
                        self.logger.debug("Inserted data for %s into database" % result[0])
                        #except AttributeError:
                    except StatementError:
                        self.logger.error("StatementError EXCEPTION on %s" % result[0])
                        pass

                    try:
                        meta_conn.execute(text(sql_meta_query))
                        self.logger.debug("Inserted metaData for %s into database [created]" % result[0])
                    except IntegrityError:
                        meta_conn.execute(text(sql_meta_query_update))
                        self.logger.debug("Updated metaData for %s in database [updated]" % result[0])

            self.logger.info("Inserted %s" % inserts)

        finally:
            conn.close()
            meta_conn.close()

        return


if __name__ == "__main__":
    optparser = argparse.ArgumentParser(description="Get data from whois. Destination table name is hardcoded \
    to \"whoistable\"")
    requiredNamed = optparser.add_argument_group('Required arguments')
    optparser.add_argument("-i", "--input_name", type=str, help="Input name. \
            if ends with '.csv' will be treated as CSV file input. Default: use_database")
    optparser.add_argument("-l", "--log_file", type=str,
                           help="Log filename. Default whois_scrapper.log")
    requiredNamed.add_argument("-d", "--in_db", type=str,
                           help="sqlalchemy db string\
                           Example postgres://login:pass@host.domain:5432/database", required=True)
    optparser.add_argument("-p", "--proxy", help="True or False. Default: False")
    optparser.add_argument("--loglevel", help="Default: INFO")
    optparser.add_argument("--threads", help="Number of threads for multiprocessing. Default = 2", type=int)
    optparser.add_argument("--apikeys", help="API keys for http://free-socks.in/ \
                            Example: \"apiKey1;apiKey2;...\"")
    optparser.add_argument("-q", "--input_data_query", help="Query to fetch data from SQL. Default: \
             SELECT company_domain FROM company_agg3 \
             LEFT JOIN whoistable ON company_agg3.\"company_domain\" = whoistable.\"domain_name\" \
             WHERE whoistable.domain_name IS NULL LIMIT 500000; ")
    args = optparser.parse_args()

    in_db = args.in_db
    if not args.input_name:
        input_name = "use_database"
    else:
        input_name = args.input_name

    if not args.threads:
        threads = 2
    else:
        threads = args.threads

    if not args.loglevel:
        loglevel = "INFO"
    else:
        loglevel = args.loglevel

    if not args.apikeys:
        apikeys = None
    else:
        apikeys = args.apikeys.split(";")

    if not args.proxy or apikeys is None:
        proxy = "False"
    else:
        proxy = args.proxy

    if not args.log_file:
        in_logging_filename = "whois_scrapper.log"
    else:
        in_logging_filename = args.log_file

    if not args.input_data_query:
        input_data_query = "SELECT company_domain FROM company_agg3 LEFT JOIN whoistable ON company_agg3.\"company_domain\" = whoistable.\"domain_name\" WHERE whoistable.domain_name IS NULL LIMIT 500000;"
    else:
        input_data_query = args.input_data_query

    # app = Scrapper(input_name, in_logging_filename, in_db_filename, use_proxy=proxy)
    app = Scrapper(input_name,
                   in_logging_filename,
                   in_db,
                   use_proxy=proxy,
                   input_data_query=input_data_query,
                   loglevel=loglevel,
                   apikey=None,
                   threads=threads
                   )
    app.run()
