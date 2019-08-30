from sqlalchemy import create_engine

eng = create_engine(db_filename)
conn = eng.connect()
try:
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

    # Insert metadata
    sql_query = "INSERT INTO processed_domains (domain_name) values (\"%s\")" % domain_name
    conn.execute(sql_query)

finally:
    conn.close()

"""
zabbix/Zab123Qwe!

### Find item value 
# Find out hostid of the required host by human-readable name, like Meter 123456
SELECT hostid, host from hosts where host LIKE "Meter 123456" and status = "0"

# Find out items, related to that hostid
SELECT itemid, name from items where hostid = "10349"

# Find out values of the item
SELECT * from history where itemid = "34660"
"""


def recalculate(meter, new_transform_factors):

    obis_list = None
    raw_obis_list = None

    items_id_pairs = get_items(meter, obis_list)

    change_values(items_id_pairs, new_transform_factors)
    pass


def get_items(meter, obis_codes):

    # [(raw_id, id)]
    pass


def change_values(items_id_pairs, new_transform_factors):

    pass



