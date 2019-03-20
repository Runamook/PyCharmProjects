import whois
from sqlalchemy import create_engine
from socket import timeout
# from subprocess import run


def get_whois(domain_name):
    try:
        result = whois.whois(domain_name)

    except whois.parser.PywhoisError:
        result = "NotExistent"  # No such domain
    except ConnectionResetError:
        result = "Refused"  # Trying to stop us
    except ConnectionRefusedError:
        result = "Refused"  # Trying to stop us
    except timeout:
        result = "Timeout"

    # Legacy
        # assert (isinstance(result, whois.parser.WhoisEntry)), "Not a whois.parser.WhoisEntry object"
    result = (domain_name, result)
    return result


# def get_fulltext_whois(domain_name):
#    result = run(["/usr/bin/env", "whois", domain_name], capture_output=True)
#    fulltext = result.stdout.decode("utf-8")
#    return fulltext


def delist(maybe_list):
    if type(maybe_list) == list:
        return maybe_list[0]
    else:
        return maybe_list


def create_tables(db_filename, logger):
    """
    Creating tables that doesn't exist
    """

    eng = create_engine(db_filename)
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

    if 'results' not in eng.table_names():
        conn.execute("CREATE TABLE results (domain_name TEXT, result TEXT)")

    logger.info("Created SQL tables")
    return


def synonym_finder(query, synonym_list):
    result = "notFound"

    for synonym in synonym_list:
        try:
            result = delist(query[synonym])
            break
        except KeyError:
            continue

    return result
