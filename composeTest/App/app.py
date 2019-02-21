#!/usr/bin/python
# TODO: sqlite> CREATE TABLE data ( dt INTEGER, value INTEGER, id TEXT, pop TEXT );
# TODO: sqlite> CREATE UNIQUE INDEX data_index ON data (dt, id, pop);
# TODO: insert pop as class attribute
# TODO: sqlite> CREATE TABLE devices ( id TEXT, mac TEXT );
# TODO: Handle re-registrations sqlite> CREATE UNIQUE INDEX device_index ON devices (id, mac);
# TODO: FIX GLOBAL VAR!!!
# TODO: Implicit registration - register a device when it sends data
# TODO: Concurrency issues? DB lock?

import datetime as dt

from flask import Flask
from flask_restful import Api, Resource

from webargs import fields
from webargs.flaskparser import use_kwargs, parser, abort
from sqlalchemy import create_engine
import logging

app = Flask(__name__)
api = Api(app)


class InsertDataResource(Resource):

    insertdata_args = {
        "value": fields.Int(required=True),
        "id": fields.Str(required=True)
    }

    @use_kwargs(insertdata_args)
    # You can decorate your view with use_args or use_kwargs.
    # The parsed arguments dictionary will be injected as a parameter of your view function (use_args)
    # Or as keyword arguments (use_kwargs)

    def post(self, id, value):
        timestamp = int(dt.datetime.now().strftime("%s"))
        pop = "test_rpi"

        try:
            db_connect = create_engine(db_name, echo=True)
            conn = db_connect.connect()
            conn.execute("INSERT INTO data (dt, value, id, pop) VALUES (\"%s\", \"%s\", \"%s\", \"%s\")" % (timestamp, value, id, pop))
        except Exception as e:
            return { "result" : "failure", "Exception" : e }

        sqllog.info("INSERT INTO data (dt, value, id, pop) VALUES (\"%s\", \"%s\", \"%s\", \"%s\")" % (timestamp, value, id, pop))
        return { "result" : "ok" }


class QueryDevicesResource(Resource):

    querydev_args = {"mac": fields.Str(missing="all")}

    @use_kwargs(querydev_args)
    def get(self, mac):

        try:
            db_connect = create_engine(db_name, echo=True)
            conn = db_connect.connect()
            if mac == "all":
                query = conn.execute("SELECT * from devices")
            else:
                query = conn.execute("SELECT * from devices WHERE mac = \"%s\"" % mac)
        except Exception as e:
            return { "result" : "failure", "Exception" : e }

        query_result = query.cursor.fetchall()
        applog.info("Found in DB %s" % query_result)
        result = {'result': query_result}
        return result


class QueryDataResource(Resource):

    querydata_args = {
        "id": fields.Str(required=True),
    }

    @use_kwargs(querydata_args)
    def get(self, id):

        try:
            db_connect = create_engine(db_name, echo=True)
            conn = db_connect.connect()
            query = conn.execute("SELECT dt, value from data WHERE id = \"%s\"" % id)
        except Exception as e:
            return { "result" : "failure", "Exception" : e }

        query_result = query.cursor.fetchall()
        applog.info("Found in DB %s" % query_result)
        result = {'result': query_result}
        return result

    # This error handler is necessary for usage with Flask-RESTful
    @parser.error_handler
    def handle_request_parsing_error(err, req, schema, error_status_code, error_headers):
        """webargs error handler that uses Flask-RESTful's abort function to return
        a JSON error response to the client.
        """
        abort(error_status_code, errors=err.messages)


def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


if __name__ == "__main__":
    api.add_resource(InsertDataResource, "/insertdata")
    api.add_resource(QueryDevicesResource, "/devices")
    api.add_resource(QueryDataResource, "/querydata")
    global db_name
    db_name = "sqlite:////home/egk/PycharmProjects/composeTest/App/sensors.db"
    # logging.basicConfig(filename= "/home/egk/PycharmProjects/composeTest/app/app.log", level = logging.INFO)
    applog = setup_logger("WebApplication", "/home/egk/PycharmProjects/composeTest/App/app.log")
    sqllog = setup_logger("SQL", "/home/egk/PycharmProjects/composeTest/App/sql.log")
    app.run(port=5001, debug=True)
