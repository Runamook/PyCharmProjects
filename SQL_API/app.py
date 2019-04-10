from flask import Flask, jsonify
import json

app = Flask(__name__)


@app.route('/meters')
def get_all_data():
    with open("/home/egk/PycharmProjects/SQL_API/jdata", "r") as jdata:
        j = json.load(jdata)
    return jsonify(j)


@app.route('/meters/<meter_number>')
def get_meter_data(meter_number):
    return_value = {}
    with open("/home/egk/PycharmProjects/SQL_API/jdata", "r") as jdata:
        j = json.load(jdata)
        for meter in j:
            if meter['IdentificationNumber'] == str(meter_number):
                return_value = meter
            return jsonify(return_value)


@app.route('/discovery')
def discovery():
    with open("/home/egk/PycharmProjects/SQL_API/discovery.json", "r") as jdata:
        j = json.load(jdata)
    return jsonify(j)


@app.route('/discovery2')
def discovery2():
    j = [{"meterName": "04690915"}, {"meterName": "04389660"}]
    return jsonify(j)


@app.route('/')
def hello():
    return 'It works!'


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
