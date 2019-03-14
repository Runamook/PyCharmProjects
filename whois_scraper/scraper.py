import whois
from sqlalchemy import create_engine
import csv
import logging
import datetime
from socket import timeout
import sys
from time import sleep

def parse_file(csv_filename):
    """
    Takes csv_filename returns list of lists
    [[domain,NS,country,create_date,expiry_date]...]
    """
    fqdn_data_list = []
    with open(csv_filename, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            fqdn_data_list.append(row)
    return fqdn_data_list


def send_whois_query(fqnd_data_list, repeat_on_timeout=True):
    """
    Sends whois query and writes data to DB
    domain,NS,country,create_date,expiry_date
    """

    for fqdn_dataset in fqnd_data_list:

        if "." not in fqdn_dataset[0]:
            # Probably header
            continue

        logging.info("Searching for %s" % fqdn_dataset[0])

        if repeat_on_timeout:
            # Re-run timed out queries

            i = 0
            while i < 3:

                try:
                    query = whois.whois(fqdn_dataset[0])
                    # Bypass further checks
                    i = 4
                except whois.parser.PywhoisError as e:
                    logging.info("%s not found" % fqdn_dataset[0])
                    i = 4
                except timeout:
                    logging.info("Timeout for %s, trying once again" % fqdn_dataset[0])
                except ConnectionResetError:
                    logging.warning("Connection reset for %s, trying once again after pause" % fqdn_dataset[0])
                    sleep(1)
                except ConnectionRefusedError:
                    logging.warning("Connection refused for %s, trying once again after pause" % fqdn_dataset[0])
                    sleep(1)
                finally:
                    i += 1
            if i == 3:
                logging.warning("%s - unable to get" % fqdn_dataset[0])
                continue

        else:
            try:
                query = whois.whois(fqdn_dataset[0])
            except whois.parser.PywhoisError as e:
                logging.info("%s not found" % fqdn_dataset[0])
                continue
            except timeout:
                logging.info("Timeout for %s" % fqdn_dataset[0])
                continue
            except ConnectionResetError:
                logging.warning("Connection reset for %s" % fqdn_dataset[0])
                continue
            except ConnectionRefusedError:
                    logging.warning("Connection refused for %s" % fqdn_dataset[0])

        write_db(fqdn_dataset, query)

    return


def delist(maybe_list):

    if type(maybe_list) == list:
        return maybe_list[0]
    else:
        return maybe_list


def write_db(fqdn_dataset, query):
    """
    Write to database
    """
    assert (isinstance(query, whois.parser.WhoisEntry)), "Not a whois.parser.WhoisEntry object"

    eng = create_engine("sqlite:////home/egk/Work/Misc/DNS_Scrapping/random.db")
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
    domain_name = delist(query['domain_name'])

    name = synonym_finder(query, ['name', 'person', 'owner', 'admin_name'])
    org = synonym_finder(query, ['org', 'tech_org'])
    country = synonym_finder(query, ['country', 'admin_country'])
    city = synonym_finder(query, ['city', 'admin_city'])
    address = synonym_finder(query, ['address', 'admin_address1'])
    creation_date = synonym_finder(query, ['creation_date', 'created'])
    expiration_date = synonym_finder(query, ['expiration_date', 'expires'])
    blob = query.__repr__()


    """
    creation_date = query['creation_date']
    expiration_date = query['expiration_date']
    updated_date = query['updated_date']
    name_servers = query['name_servers']
    status = query['status']
    emails = query['emails']
    dnssec = query['dnssec']
    name = query['name']
    org = query['org']
    address = query['address']
    city = query['city']
    state = query['state']
    zipcode = query['zipcode']
    country = query['country']
    registrar = query['registrar']
    whois_server = query['whois_server']
    referral_url = query['referral_url']
    """

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


def synonym_finder(query, synonym_list):
    result = "notFound"

    for synonym in synonym_list:
        try:
            result = delist(query[synonym])
            break
        except KeyError:
            continue

    if result == "notFound":
        logging.warning("Unable to find synonym %s %s" % (delist(query.domain_name), synonym_list[0]))

    return result


def meta(csv_filename):
    dt_start = datetime.datetime.now()
    fqdn_data_list = parse_file(csv_filename)
    send_whois_query(fqdn_data_list)

    dt_stop = datetime.datetime.now()
    delta = dt_stop - dt_start

    logging.info("Completed in %s seconds" % delta.seconds)


if __name__ == "__main__":

    csv_filename = sys.argv[1]
    logging_filename = sys.argv[2]

    fmt = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(format=fmt, level=logging.INFO, filename=logging_filename)

    # csv_filename = '/home/egk/Work/Misc/DNS_Scrapping/random_small.csv'
    # dbfile = '/home/egk/Work/Misc/DNS_Scrapping/random.db'

    meta(csv_filename)
