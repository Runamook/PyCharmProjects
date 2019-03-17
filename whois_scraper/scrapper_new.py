# from sqlalchemy import create_engine
# from sqlalchemy.exc import OperationalError
import csv
import whois
import time
import sys
from whois_scraper.helper_functions import helper_functions, create_logger, synonyms
from multiprocessing.dummy import Pool

# TODO: Split input into buckets


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
        self.pool = Pool(16)

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

    def run(self):

        self.results = self.pool.map(helper_functions.get_whois, self.domains)
        # [(domain_name, whois_results ),(),()...]
        for result in self.results:
            self.log_result(result)

            # self.write_db(result)

        return

    def write_to_db(self, result):

        return


if __name__ == "__main__":
    if len(sys.argv) < 4:
        # in_csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.csv"
        in_csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random.csv"
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
