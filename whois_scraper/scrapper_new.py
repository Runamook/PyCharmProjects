from sqlalchemy import create_engine
from sqlalchemy import text
import csv
import whois
import time
import sys
import datetime
from whois_scraper.helper_functions import helper_functions, create_logger, synonyms
from multiprocessing.dummy import Pool
from time import sleep

# TODO: Use SQL ORM
# TODO: TLD separator (maybe separate)
# TODO change "Privacy" names to something else


class Scrapper:
    def __init__(self, csv_filename, log_filename, db_filename):

        self.csv_filename = csv_filename
        self.db_filename = db_filename
        # Lists of synonyms
        self.synonyms = synonyms.Synonyms()
        # Logging config
        self.logger = create_logger.create_logger(log_filename, __name__)
        self.results = None

        self.refused_counter = 0
        self.pause_times = {    # Refuses : Seconds
            10: 20,             # 10 is mandatory
            40: 60,
            80: 120,
            99: 180
        }

        self.domains = self.parse_input()

        pool_size = 32              # Multi-thread flows
        bucket_size = 100           # Domains processed at once
        self.buckets_processed = 0
        self.logger.info("Created Scrapper object\n\t\tPool size = %s\n\t\tBucket size = %s" % (pool_size, bucket_size))
        # Create tables
        helper_functions.create_tables(self.db_filename, self.logger)

        # Multi thread pool
        self.bucket_size = bucket_size
        self.pool = Pool(pool_size)

    def parse_input(self):
        """
        Parses CSV file and returns list of domains
        [domainA,domainB,domainC,...]
        """
        result = []
        start_time = time.time()
        with open(self.csv_filename, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if "." in row[0]:
                    result.append(row[0])
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
        eng = create_engine(self.db_filename)
        conn = eng.connect()

        results = []
        try:
            for domain_name in bucket:
                sql_query = "SELECT result FROM results WHERE domain_name = \'%s\'" % domain_name
                status = conn.execute(sql_query)
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
            conn.close()

        self.logger.info("Bucket shrinked to %s" % len(results))
        return results

    def run(self):

        self.bucketize()

        for bucket in self.domains:
            self.check_if_pause_needed()
            self.logger.info("Starting bucket, %s already processed" % self.buckets_processed)
            bucket = self.check_bucket(bucket)

            self.results = self.pool.map(helper_functions.get_whois, bucket)

            self.write_all_to_db()
            self.buckets_processed += 1

        return

    def check_if_pause_needed(self):
        self.logger.info("Refused counter\t\t\t=\t\t\t[%s]" % self.refused_counter)
        sleep(0.00001)

        if self.refused_counter > 10:
            pause_time = 10     # Default fallback
            for counter in self.pause_times:
                if self.refused_counter > self.pause_times[counter]:
                    pause_time = self.pause_times[counter]
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
        conn = eng.connect()

        inserts = 0
        try:

            for result in self.results:

                self.log_result(result)
                if result[1] not in ["NotExistent", "Refused", "Timeout"]:
                    assert (isinstance(result[1], whois.parser.WhoisEntry)),\
                        "Not a whois.parser.WhoisEntry object\n%s" % result

                    sql_meta_query = "INSERT INTO results ( \
                        domain_name, \
                        result\
                        ) values (\'%s\', \'Processed\') ON CONFLICT (domain_name) DO UPDATE SET \
                         result = \'Processed\'" % result[0]
                    mark = "ok"
                    inserts += 1
                else:

                    sql_meta_query = "INSERT INTO results ( \
                        domain_name, \
                        result\
                        ) values (\'%s\', \'%s\') ON CONFLICT (domain_name) DO UPDATE SET \
                         result = \'%s\'" % (result[0], result[1], result[1])
                    mark = "continue"

                if mark == "continue":
                    # Not processing further - nothing to insert
                    conn.execute(sql_meta_query)
                    self.logger.debug("Inserted metadata for %s into database [skipped]" % result[0])
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
                    expiration_date = helper_functions.synonym_finder(result[1], self.synonyms.synonym_expiration_date)
                    # Others are processed using helper_functions.sanitize()
                    blob = result[1].text.replace("'", '"').replace("\0", " ").strip(" \t\r\n\0")
                    # blob = helper_functions.sanitize(result[1].text).strip(" \t\r\n\0")

                    # Insert record
                    sql_query = "INSERT INTO domains (\
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
                        ) values (\'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\')" % (
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

                    # self.logger.debug(sql_query)
                    # https://docs.sqlalchemy.org/en/latest/core/tutorial.html#using-textual-sql
                    conn.execute(text(sql_query))
                    self.logger.debug("Inserted data for %s into database" % result[0])
                    conn.execute(text(sql_meta_query))

                    self.logger.debug("Inserted metadata for %s into database [created]" % result[0])
        except Exception as e:
            # self.logger.error("EXCEPTION on %s" % result)
            raise e

        finally:
            conn.close()
        self.logger.info("Inserted %s" % inserts)

        return


if __name__ == "__main__":
    if len(sys.argv) < 4:
        # in_csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.csv"
        in_csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random.csv"
        in_logging_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.log"
        # in_db_file = "/home/egk/Work/Misc/DNS_Scrapping/random_small.db"
        # in_db_filename = "sqlite:///" + in_db_file
        in_db_filename = "postgres://serp:serpserpserpserpserp@127.0.0.1:5432/postgres"
    else:
        in_csv_filename = sys.argv[1]
        in_logging_filename = sys.argv[2]
        in_db_file = sys.argv[3]
        in_db_filename = "sqlite:///" + in_db_file

    app = Scrapper(in_csv_filename, in_logging_filename, in_db_filename)
    app.run()
