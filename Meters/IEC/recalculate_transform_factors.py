from sqlalchemy import create_engine

# pip install mysql-connector-python
# pip install sqlalchemy

"""
ssh -L 13306:localhost:3306 host

### Find item value 
# Find out hostid of the required host by human-readable name, like Meter 123456
SELECT hostid, host from hosts where host LIKE "Meter 123456" and status = "0"

# Find out items, related to that hostid
SELECT itemid, name from items where hostid = "10349"

# Find out values of the item
SELECT * from history where itemid = "34660"

# Update the value
UPDATE history SET value = 1.1 where itemid = "42589" and clock = 1567399500

with tt2 as (select * from tt)
update tt set tt.value = tt.value*2 where exists (select from tt2 where tt2.dt=tt.dt and tt2.id='f1') and tt.id='f2'
"""


class Meter:

    def __init__(self,
                 meter_name,
                 obis_raw,
                 obis_derived,
                 transform_factors,
                 db="mysql://user:pass@127.0.0.1:13306/zabbix"
                 ):

        self.meter_name = meter_name
        self.obis_raw = obis_raw
        self.obis_derived = obis_derived
        self.transform_factors = transform_factors
        self.conn = create_engine(db).connect()

        self.host_id = None
        self.obis_raw_id = None
        self.obis_derived_id = None

    def _get_host_id(self):
        sql_query = f'SELECT hostid, host from hosts where host LIKE "Meter {self.meter_name}" and status = "0"'
        print(sql_query)
        result = self._execute_query(sql_query)      # [(10367, 'Meter metername')]
        self.host_id = result[0][0]
        print(f'Hostid = {self.host_id}')

    def _get_items(self):
        sql_query = f'SELECT itemid, name from items where hostid = "{self.host_id}"'
        print(sql_query)
        result = self._execute_query(sql_query)      # [(42521, 'metricname'), (), ()]
        for item in result:
            if item[1] == self.obis_raw:
                self.obis_raw_id = item[0]
            elif item[1] == self.obis_derived:
                self.obis_derived_id = item[0]
        print(
            f'OBIS raw = {self.obis_raw}: {self.obis_raw_id}, derived = {self.obis_derived}: {self.obis_derived_id}'
        )

    def _execute_query(self, query):
        """
        :param query:
        :return: [(), (), ()]
        """
        try:
            return list(self.conn.execute(query))
        except:
            self.conn.close()

    def recalculate(self):

        query_raw_items = f'SELECT * FROM history WHERE itemid = "{self.obis_raw_id}"'
        raw_list = self._execute_query(query_raw_items)              # [(42589, 1554378300, 0.0, 2), (), ()]
        print(f'Got {len(raw_list)} items')

        counter = 0
        for item in raw_list:
            dt = item[1]
            raw_value = item[2]
            if raw_value == 0:
                # Skip 0, no transformation applied
                continue
            new_value = raw_value * self.transform_factors
            sql_query_u = f'UPDATE history SET value = {new_value} WHERE itemid = "{self.obis_derived_id}" AND clock = {dt}'
            counter += 1
            print(sql_query_u)
            # self._execute_query(sql_query)
            # self.conn.execute(sql_query_u)
            if counter % 100 == 0:
                print(f'{counter} of {len(raw_list)} processed')
        print(f'{counter} records processed')

    def run(self):
        self._get_host_id()
        self._get_items()
        self.recalculate()
        self.conn.close()


if __name__ == '__main__':
    metername = "1MSC0010001210"
    obisderived = "Negative active demand OBIS 2.5.0 (Billing data)"
    obisraw = "Negative active demand OBIS 2.5.0 (Billing data) (Raw)"
    transform = {'current': 200, 'voltage': 5, 'total': 1000}
    d = 'mysql://zabbix:Zab123Qwe!@127.0.0.1:13306/zabbix'

    m = Meter(
        meter_name=metername,
        obis_raw=obisraw,
        obis_derived=obisderived,
        db=d,
        transform_factors=transform['total']
    )

    m.run()


