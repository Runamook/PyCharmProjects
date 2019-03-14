import whois
from sqlalchemy import create_engine
import csv
import logging
import datetime
from socket import timeout
from time import sleep


filename = '/home/egk/Work/Misc/DNS_Scrapping/random_small.csv'
dbfile = '/home/egk/Work/Misc/DNS_Scrapping/random.db'


def parse_file(filename):
    """
    Takes filename returns list of lists
    [[domain,NS,country,create_date,expiry_date]...]
    """
    fqdn_data_list = []
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            fqdn_data_list.append(row)
    return fqdn_data_list


def send_whois_query(fqnd_data_list, repeat_on_timeout=False):
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

            args = fqdn_dataset[0] + " --quick"
            i = 0
            while i < 3:

                try:
                    # query = whois.whois(fqdn_dataset[0])
                    query = whois.whois(args)
                    # Bypass further checks
                    i = 4
                except whois.parser.PywhoisError as e:
                    logging.info("%s not found" % fqdn_dataset[0])
                    i = 4
                except timeout:
                    logging.info("Timeout for %s, trying once again" % fqdn_dataset[0])
                except ConnectionResetError:
                    logging.info("Connection reset for %s, trying once again" % fqdn_dataset[0])
                finally:
                    i += 1
                    if i == 3:
                        logging.warning("%s - unable to get" % fqdn_dataset[0])
        else:
            try:
                query = whois.whois(fqdn_dataset[0])
            except whois.parser.PywhoisError as e:
                logging.info("%s not found" % fqdn_dataset[0])
            except timeout:
                logging.info("Timeout for %s" % fqdn_dataset[0])
            except ConnectionResetError:
                logging.info("Connection reset for %s" % fqdn_dataset[0])

        write_db(fqdn_dataset, query)

    return


def write_db(fqdn_dataset, query):
    """
    Write to database
    """
    eng = create_engine("sqlite:////home/egk/Work/Misc/DNS_Scrapping/random.db")
    conn = eng.connect()

    if 'domains' not in eng.table_names():
        conn.execute(
            "CREATE TABLE domains (dt TIMESTAMP, domain_name TEXT, registrar TEXT, whois_server TEXT, referral_url TEXT, updated_date TIMESTAMP, creation_date TIMESTAMP, expiration_date TIMESTAMP, name_servers TEXT, status TEXT, emails TEXT, dnssec TEXT, name TEXT, org TEXT, address TEXT, city TEXT, state TEXT, zipcode TEXT, country TEXT)")

    dt = str(datetime.datetime.now())
    domain_name = query['domain_name'][1]
    registrar = query['registrar']
    whois_server = query['whois_server']
    referral_url = query['referral_url']

    if type(query['updated_date']) == list:
        updated_date = query['updated_date'][1]
    else:
        updated_date = query['updated_date']

    creation_date = query['creation_date']
    expiration_date = query['expiration_date']
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
    person
    owner
    admin_name
    admin_email
    admin_phone

    try:
        sql_query = "INSERT INTO domains (dt, domain_name, registrar, whois_server, referral_url, updated_date, creation_date, expiration_date, name_servers, status, emails, dnssec, name, org, address, city, state, zipcode, country) values (\"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\")" % (
        dt, domain_name, registrar, whois_server, referral_url, updated_date, creation_date, expiration_date,
        name_servers, status, emails, dnssec, name, org, address, city, state, zipcode, country)
        conn.execute(sql_query)
    finally:
        # conn.commit()
        conn.close()

    return


def meta(filename):
    dt_start = datetime.datetime.now()
    FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    fqdn_data_list = parse_file(filename)
    send_whois_query(fqdn_data_list)

    dt_stop = datetime.datetime.now()
    delta = dt_stop - dt_start

    logging.info("Completed in %s seconds" % delta.seconds)


meta(filename)