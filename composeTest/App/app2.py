#!/usr/bin/python

from flask import Flask
import datetime as dt
from webargs import fields
from webargs.flaskparser import use_kwargs, parser, abort
from sqlalchemy import create_engine

app = Flask(__name__)

hello_args = {"name": fields.Str(missing="Friend")}

@app.route("/", methods=["GET"])
@use_args(hello_args)
def index(args):
    """A welcome page.
    """
    return jsonify({"message": "Welcome, {}!".format(args["name"])})


add_args = {"x": fields.Float(required=True), "y": fields.Float(required=True)}


@app.route("/add", methods=["POST"])
@use_kwargs(add_args)
def add(x, y):
    """An addition endpoint."""
    return jsonify({"result": x + y})


dateadd_args = {
    "value": fields.Date(required=False),
    "addend": fields.Int(required=True, validate=validate.Range(min=1)),
    "unit": fields.Str(missing="days", validate=validate.OneOf(["minutes", "days"])),
}


@app.route("/dateadd", methods=["POST"])
@use_kwargs(dateadd_args)
def dateadd(value, addend, unit):
    """A date adder endpoint."""
    value = value or dt.datetime.utcnow()
    if unit == "minutes":
        delta = dt.timedelta(minutes=addend)
    else:
        delta = dt.timedelta(days=addend)
    result = value + delta
    return jsonify({"result": result.isoformat()})


# Return validation errors as JSON
@app.errorhandler(422)
@app.errorhandler(400)
def handle_error(err):
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])
    if headers:
        return jsonify({"errors": messages}), err.code, headers
    else:
        return jsonify({"errors": messages}), err.code


if __name__ == "__main__":
app.run(port=5001, debug=True)