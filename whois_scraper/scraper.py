import whois
from sqlalchemy import create_engine
import csv
import logging
import datetime
from socket import timeout
import sys
from time import sleep


class Scrapper():
    def __init__(self, csv_filename, log_filename, db_filename, repeat_on_timeout=False, repeats=3):

        self.csv_filename = csv_filename
        self.fqdn_data_list = self.parse_file()
        self.repeat_on_timeout = repeat_on_timeout
        self.repeats = int(repeats)
        self.db_filename = db_filename

        # Lists of synonyms
        self.synonym_name = ['name', 'person', 'owner', 'admin_name']
        self.synonym_org = ['org', 'tech_org']
        self.synonym_country = ['country', 'admin_country']
        self.synonym_city = ['city', 'admin_city']
        self.synonym_address = ['address', 'admin_address1']
        self.synonym_creation_date = ['creation_date', 'created']
        self.synonym_expiration_date = ['expiration_date', 'expires']

        # Logging config
        self.logger = logging.getLogger("Scrapper")
        self.logger.setLevel(logging.INFO)
        self.fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        self.fh = logging.FileHandler(filename=log_filename)
        self.fh.setFormatter(self.fmt)
        self.fh.setLevel(logging.INFO)

        self.fh.setFormatter(self.fmt)
        self.logger.addHandler(self.fh)

    def parse_file(self):
        """
        Takes csv_filename returns list of lists
        [[domain,NS,country,create_date,expiry_date]...]
        """
        fqdn_data_list = []
        with open(self.csv_filename, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                fqdn_data_list.append(row)
        return fqdn_data_list

    def send_whois_query(self):
        """
        Sends whois query and writes data to DB
        domain,NS,country,create_date,expiry_date
        """

        for fqdn_dataset in self.fqdn_data_list:

            if "." not in fqdn_dataset[0]:
                # Probably header
                continue

            self.logger.info("Searching for %s" % fqdn_dataset[0])

            if self.repeat_on_timeout:
                # Re-run timed out queries

                i = 0
                while i < self.repeats:

                    try:
                        query = whois.whois(fqdn_dataset[0])
                        # Bypass further checks
                        i = self.repeats + 1
                    except whois.parser.PywhoisError:
                        self.logger.info("%s not found" % fqdn_dataset[0])
                        i = self.repeats + 1
                    except timeout:
                        self.logger.info("Timeout for %s, trying once again" % fqdn_dataset[0])
                    except ConnectionResetError:
                        # Being gentle
                        self.logger.warning("Connection reset for %s, NOT trying once again" % fqdn_dataset[0])
                        i = self.repeats + 1
                        sleep(1)
                    except ConnectionRefusedError:
                        self.logger.warning("Connection refused for %s, NOT trying once again" % fqdn_dataset[0])
                        i = self.repeats + 1
                        sleep(1)
                    finally:
                        i += 1
                if i == self.repeats:
                    self.logger.warning("%s - unable to get" % fqdn_dataset[0])
                    continue

            else:
                try:
                    query = whois.whois(fqdn_dataset[0])
                except whois.parser.PywhoisError:
                    self.logger.info("%s not found" % fqdn_dataset[0])
                    continue
                except timeout:
                    self.logger.info("Timeout for %s" % fqdn_dataset[0])
                    continue
                except ConnectionResetError:
                    self.logger.warning("Connection reset for %s" % fqdn_dataset[0])
                    continue
                except ConnectionRefusedError:
                    self.logger.warning("Connection refused for %s" % fqdn_dataset[0])

            self.write_db(query)

        return

    def delist(self, maybe_list):

        if type(maybe_list) == list:
            return maybe_list[0]
        else:
            return maybe_list

    def write_db(self, query):
        """
        Write to database
        """
        assert (isinstance(query, whois.parser.WhoisEntry)), "Not a whois.parser.WhoisEntry object"

        eng = create_engine(self.db_filename)
        conn = eng.connect()

        if 'domains' not in eng.table_names():
            conn.execute("CREATE TABLE domains (\
            dt TIMESTAMP, \
            domain_name TEXT, \
            name TEXT, \
            org TEXT, \
            country TEXT, \
            city TEXT, \
            address TEXT, \
            creation_date TIMESTAMP, \
            expiration_date TIMESTAMP, \
            blob TEXT)"
                         )

        dt = str(datetime.datetime.now())
        domain_name = self.delist(query['domain_name'])

        name = self.synonym_finder(query, self.synonym_name)
        org = self.synonym_finder(query, self.synonym_org)
        country = self.synonym_finder(query, self.synonym_country)
        city = self.synonym_finder(query, self.synonym_city)
        address = self.synonym_finder(query, self.synonym_address)
        creation_date = self.synonym_finder(query, self.synonym_creation_date)
        expiration_date = self.synonym_finder(query, self.synonym_expiration_date)
        blob = query.__repr__()

        try:
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
        finally:
            conn.close()

        return

    def synonym_finder(self, query, synonym_list):
        result = "notFound"

        for synonym in synonym_list:
            try:
                result = self.delist(query[synonym])
                break
            except KeyError:
                continue

        if result == "notFound":
            self.logger.warning("Unable to find synonym %s %s" % (self.delist(query.domain_name), synonym_list[0]))

        return result

    def main(self):

        dt_start = datetime.datetime.now()
        self.send_whois_query()
        dt_stop = datetime.datetime.now()
        delta = dt_stop - dt_start

        self.logger.info("Completed in %s seconds" % delta.seconds)


if __name__ == "__main__":

    # csv_filename = sys.argv[1]
    # logging_filename = sys.argv[2]
    # db_filename = sys.argv[2]

    csv_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.csv"
    logging_filename = "/home/egk/Work/Misc/DNS_Scrapping/random_small.log"
    db_filename = "sqlite:////home/egk/Work/Misc/DNS_Scrapping/random_small.db"

    app = Scrapper(csv_filename, logging_filename, db_filename)
    app.main()

