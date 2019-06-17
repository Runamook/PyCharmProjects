import requests
import json
from sqlalchemy import create_engine
import time


def timer_decorator(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        delta = time.time() - start
        print(f"Took {delta} seconds")

    return wrapper


class Json2Sql:

    table = "meters"

    def __init__(self, uri, sqlite_db):
        self.uri = uri
        self.engine = create_engine(f'sqlite:///{sqlite_db}')
        self.conn = self.engine.connect()
        self.inserts = []

    @timer_decorator
    def _get_data(self):
        """
        {
        "meterNumber":"04770299",
        "manufacturer":"EMH",
        "ip":"10.124.0.84",
        "installationDate":"2014-07-29T12:00:00",
        "isActive":true,
        "voltageRatio":100,
        "currentRatio":20,
        "totalFactor":120
        }
        """
        if "http" in self.uri:
            print("Web request")
            meters = requests.get(self.uri).json()
        # elif self.uri.startswith("/"):
        else:
            print("File processing")
            with open(self.uri, "r") as f:
                meters = json.load(f)

        # print(meters)
        for meter in meters:
            self.inserts.append({
                "meterNumber": meter["meterNumber"],
                "ip": meter["ip"],
                "voltageRation": meter["voltageRatio"],
                "curentRation": meter["currentRatio"],
                "totalFactor": f"{meter['voltageRatio'] * meter['currentRatio']}"
            })
        return

    @timer_decorator
    def _create_tables(self):

        print("Creating tables")
        if self.table not in self.engine.table_names():
            self.conn.execute(f"CREATE TABLE {self.table}(\
            meterNumber TEXT, \
            ip TEXT, \
            voltageRatio TEXT, \
            currentRatio TEXT, \
            totalFactor TEXT)"
                         )
        return

    @timer_decorator
    def _db_insert(self):

        print("DB insertion")
        for insert in self.inserts:
            try:
                meterNumber = insert["meterNumber"]
                ip = insert["ip"]
                voltageRatio = insert["voltageRatio"]
                curentRatio = insert["curentRatio"]
                totalFactor = insert["totalFactor"]
            except KeyError:
                # print(f"KeyError while processing {insert}")
                meterNumber = insert["meterNumber"]
                ip = insert["ip"]
                voltageRatio = insert["voltageRation"]
                curentRatio = insert["curentRation"]
                totalFactor = insert["totalFactor"]

            query = f"INSERT INTO {self.table} (meterNumber, ip, voltageRatio, currentRatio, totalFactor) \
            values ('{meterNumber}', '{ip}', '{voltageRatio}', '{curentRatio}', '{totalFactor}' );"
            self.conn.execute(query)
        return

    def run(self):
        self._create_tables()
        self._get_data()
        self._db_insert()


if __name__ == "__main__":
    url = 'http://10.11.30.97:5000/api/meterpinginfo'
    uri = "/home/egk/Pile/Coursera/w5/test"
    db = "/home/egk/Pile/Coursera/w5/meters.db"

    app = Json2Sql(url, db)
    app2 = Json2Sql(uri, db)

    app.run()
    app2.run()


