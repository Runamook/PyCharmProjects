from flask import Flask, jsonify

app = Flask(__name__)

meter_icmp_list = [
    {
        "MeterNumber": "05939068",
        "IP": "10.124.1.12"
     },
    {
        "MeterNumber": "05939061",
        "IP": "10.124.1.41"
    },
    {
        "MeterNumber": "03429049",
        "IP": "10.124.1.128"
    },
    {
        "MeterNumber": "05896203",
        "IP": "10.124.2.15"
    },
    {
        "MeterNumber": "05896204",
        "IP": "10.124.2.103"
    },
    {
        "MeterNumber": "06205102",
        "IP": "10.124.2.111"
    },
    {
        "MeterNumber": "05222613",
        "IP": "10.124.2.114"
    },
    {
        "MeterNumber": "07279397",
        "IP": "10.124.2.116"
    },
    {
        "MeterNumber": "05939038",
        "IP": "10.124.2.117"
    },
    {
        "MeterNumber": "05296170",
        "IP": "10.124.2.120"
    }
]

# GET /books
@app.route('/meters.json')
def get_meter_icmp_list():
    return jsonify({'books': meter_icmp_list})


if __name__ == "__main__":
    app.run(host="127.0.0.1")
