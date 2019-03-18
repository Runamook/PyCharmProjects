from sqlalchemy import create_engine
# from sqlalchemy.exc import OperationalError
import csv
import whois
import time
import sys
import datetime
from whois_scraper.helper_functions import helper_functions, create_logger, synonyms
from multiprocessing.dummy import Pool

# TODO: Split input into buckets
# TODO: Write whole bucket into DB

class Scrapper:
    def __init__(self, csv_filename, log_filename, db_filename):

        self.csv_filename = csv_filename
        self.db_filename = db_filename
        # Lists of synonyms
        self.synonyms = synonyms.Synonyms()
        # Logging config
        self.logger = create_logger.create_logger(log_filename, __name__)
        self.results = None

        self.domains = self.parse_input()

        # Create tables
        helper_functions.create_tables(self.db_filename, self.logger)

        # Multi thread pool
        self.bucket_size = 100
        self.pool = Pool(32)

    def parse_input(self):
        """
        Parses CSV file and returns list of domains
        [domainA,domainB,domainC,...]
        """
        result = []
        start_time = time.time()
        with open(self.csv_filename, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if "." in row[0]:
                    result.append(row[0])
        delta = str(time.time() - start_time)
        self.logger.info("Parsed input in %s seconds, %s domains found" % (delta, str(len(result))))
        return result

    def log_result(self, result):
        if result[1] == "NotExistent":  # Result value
            self.logger.warning("%s --- Not Found" % result[0])
        elif result[1] == "Refused":
            self.logger.warning("%s --- Refused" % result[0])
        elif result[1] == "Timeout":
            self.logger.warning("%s --- Tiemout" % result[0])
        elif isinstance(result[1], whois.parser.WhoisEntry):
            self.logger.info("%s --- Found" % result[0])

        else:
            self.logger.error("Something goes wrong %s --- %s" % (result[0], result[1]))

        return

    def check_duplicates(self):

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
        return

    def run(self):

        self.bucketize()

        for bucket in self.domains:
            self.logger.log("Starting bucket")
            self.results = self.pool.map(helper_functions.get_whois, bucket)
            # [(domain_name, whois_results ),(),()...]
            for result in self.results:
                self.log_result(result)
                self.write_to_db(result)

        return

    def write_to_db(self, result):
        """
        Write to database
        """

        eng = create_engine(self.db_filename)
        conn = eng.connect()

        # Insert into results
        try:
            if result[1] not in ["NotExistent", "Refused", "Timeout"]:
                assert (isinstance(result[1], whois.parser.WhoisEntry)), "Not a whois.parser.WhoisEntry object\n%s" % result

                sql_query = "INSERT INTO results ( \
                domain_name, \
                result\
                ) values (\"%s\", \"Processed\")" % result[0]

            else:

                sql_query = "INSERT INTO results ( \
                domain_name, \
                result\
                ) values (\"%s\", \"%s\")" % (result[0], result[1])

            conn.execute(sql_query)
            self.logger.debug("Inserted metadata for %s into database" % result[0])

            # Insert into data
            dt = str(datetime.datetime.now())
            domain_name = result[0]

            name = helper_functions.synonym_finder(result[1], self.synonyms.synonym_name)
            org = helper_functions.synonym_finder(result[1], self.synonyms.synonym_org)
            country = helper_functions.synonym_finder(result[1], self.synonyms.synonym_country)
            city = helper_functions.synonym_finder(result[1], self.synonyms.synonym_city)
            address = helper_functions.synonym_finder(result[1], self.synonyms.synonym_address)
            creation_date = helper_functions.synonym_finder(result[1], self.synonyms.synonym_creation_date)
            expiration_date = helper_functions.synonym_finder(result[1], self.synonyms.synonym_expiration_date)
            blob = result[1].__repr__()

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
            ) values (\"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\")" % (
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
            conn.execute(sql_query)

            self.logger.debug("Inserted data for %s into database" % result[0])

        finally:
            conn.close()

        return


if __name__ == "__main__":
    if len(sys.argv) < 4:
        # in_csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.csv"
        in_csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.csv"
        in_logging_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.log"
        in_db_file = "/home/egk/Work/Misc/DNS_Scrapping/random_small.db"
        in_db_filename = "sqlite:///" + in_db_file
    else:
        in_csv_filename = sys.argv[1]
        in_logging_filename = sys.argv[2]
        in_db_file = sys.argv[3]
        in_db_filename = "sqlite:///" + in_db_file

    app = Scrapper(in_csv_filename, in_logging_filename, in_db_filename)
    app.run()
