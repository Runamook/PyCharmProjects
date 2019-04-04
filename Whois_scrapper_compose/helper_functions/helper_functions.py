import whois
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from socket import timeout
import re
from subprocess import run, PIPE
import datetime
import requests
import os, sys
from random import randint


re_keys = {
    "1-NotExistent": re.compile(".*(NOT FOUND).*"),
    "2-NotExistent": re.compile(".*(No match for domain).*"),
    "3-NotExistent": re.compile(".*(No Data Found).*"),
    "4-NotExistent": re.compile(".*(Could not retrieve Whois).*"),
    "5-NotExistent": re.compile(".*(The queried object does not exist).*"),
    "1-Refused": re.compile(".*(LIMIT EXCEEDED).*"),
    "2-Refused": re.compile(".*(You have exceeded your access quota).*")
}


def get_whois(domain_name):

    try:

        result = whois.whois(domain_name)

        # Check if the response given is really empty
        for key in re_keys:
            try:
                if re_keys[key].match(result.text):
                    result = key[2:]
                    break
            except AttributeError as e:
                # Something strange, there is a response but no text attributes
                raise AttributeError("Strange, no text attribute in response for ", domain_name, result, e)

        # If there is a response, check if domain_name != None
        # If domain_name = None, it should be captured by re_keys loop above
        # If it is not captured, but still no domain_name - we want to see it

        # In normal case whois response is a whois object with at least domain_name key
        if result not in ["NotExistent", "Refused"]:
            if "domain_name" in result.keys():
                domain_name_field = "domain_name"
            elif "domain" in result.keys():
                domain_name_field = "domain"
            else:
                # print("domain name field (\"domain_name\" or \"domain\") not found")
                result["domain_name"] = domain_name
                domain_name_field = "domain_name"
                print(domain_name, result)
            try:
                if result[domain_name_field] is None:
                    result = "Refused"
            except TypeError:
                result = "Refused"
                pass

    except whois.parser.PywhoisError:
        result = "NotExistent"  # No such domain
    except ConnectionResetError:
        result = "Refused"  # Trying to stop us
    except ConnectionRefusedError:
        result = "Refused"  # Trying to stop us
    except timeout:
        result = "Timeout"
    except OSError:
        # result = "Refused"  # Whois server unavailable
        # result = "NotExistent" # If proxy is unaccessible - all will be timed out
        result = "Timeout"
    except OperationalError:
        result = "Refused"  # http://sqlalche.me/e/e3q8

    result = (domain_name, result)
    return result


def remove_proxy():
    if 'SOCKS' in os.environ:
        del os.environ["SOCKS"]
    return


def remove_nonascii(s):
    return "".join(i for i in s if ord(i) < 128)


def sanitize(text):
    if isinstance(text, str):
        # return text.replace('"', "'").replace("\0", " ")
        return text.replace("'", '"').replace("\0", " ")
    else:
        return text


def restart_modem(logger):
    """
    Calls sakis3g (https://github.com/Trixarian/sakis3g-source) to restart 3G modem
    :param logger:
    :return:
    """
    dt_start = datetime.datetime.now()
    ip_old = run(["/usr/bin/curl", "-s", "https://ipinfo.io/ip"], stdout=PIPE).stdout.strip().decode("utf-8")
    run(["/usr/bin/sakis3g",
         "reconnect",
         "CUSTOM_APN=internet.tele2.ru",
         "--sudo",
         "APN=CUSTOM_APN",
         "APN_USER=tele2",
         "APN_PASS=tele2"])
    ip_new = run(["/usr/bin/curl", "-s", "https://ipinfo.io/ip"], stdout=PIPE).stdout.strip().decode("utf-8")

    dt_stop = datetime.datetime.now()
    delta = dt_stop - dt_start

    if ip_old == ip_new:
        logger.error("Unable to change IP")
        raise Exception("IPChangeError")
    else:
        logger.info("Changed IP from %s to %s in %s seconds" % (ip_old, ip_new, delta.seconds))

        return


def change_proxy(apikey):
    socks_proxy = get_proxy(apikey)
    os.environ["SOCKS"] = socks_proxy

    return socks_proxy


def get_proxy(apikeys):
    # https://free-socks.in/api/v1/get_proxy?apikey=Token&protocol[]=socks5&max_latency=1

    apikey = apikeys[randint(0, len(apikeys[:-1]))]
    url = "https://free-socks.in/api/v1/get_proxy?apikey=%s&protocol[]=socks5&max_latency=1" % apikey
    response = requests.get(url).json()

    assert response["status"] != "error", "API returned error %s on %s" % (response, url)
    socks_proxy = response["data"][0]["ip"] + ":" + str(response["data"][0]["port"])

    return socks_proxy


def delist(maybe_list):
    if type(maybe_list) == list:
        return maybe_list[0]
    else:
        return maybe_list


def create_tables(db_filename, meta_db_filename, logger):
    """
    Creating tables that doesn't exist
    """

    try:

        eng = create_engine(db_filename)
        meta_eng = create_engine(meta_db_filename)

        conn = eng.connect()
        meta_conn = meta_eng.connect()

        if 'whoistable' not in eng.table_names():
            conn.execute("CREATE TABLE whoistable (\
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

        if 'results' not in meta_eng.table_names():
            meta_conn.execute("CREATE TABLE results (domain_name TEXT, result TEXT)")

        logger.info("Created tables")

        meta_conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS domain_name_index on results (domain_name)")
        meta_conn.execute("CREATE INDEX IF NOT EXISTS results_index on results (result)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS domain_name_data_index ON public.whoistable (domain_name)")
        # CREATE UNIQUE INDEX whoistable_domain_name_idx ON public.whoistable (domain_name);
        logger.info("Created indexes")
    except Exception as e:
        raise e
    finally:
        conn.close()
        meta_conn.close()
        return


def synonym_finder(query, synonym_list):
    result = "notFound"

    for synonym in synonym_list:
        try:
            result = delist(query[synonym])
            break
        except KeyError:
            continue

    return sanitize(result)
