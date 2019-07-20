from flask import Flask, jsonify
from sqlalchemy import create_engine

app = Flask(__name__)


def meters_from_db(db_file):
    if not db_file.startswith("/"):
        print(f"{db_file} does not look like an absolute path")
        raise ValueError
    if not db_file.startswith("sqlite:///"):
        db_file = f"sqlite:///{db_file}"
        # print(db_file)

    engine = create_engine(db_file)
    conn = engine.connect()

    query = "SELECT meterNumber, tag FROM meters ORDER BY meterNumber ASC;"
    db_response = conn.execute(query).fetchall()
    # meter_list = [{"MeterId": meter_tuple[0].replace("'", '"')} for meter_tuple in db_response]
    tuple_list = list(filter(lambda x: x[1] == "frequent", db_response))
    meter_list = [{"MeterId": x[0].replace("'", '"')} for x in tuple_list]

    return meter_list

# GET /meters.json
@app.route('/meters.json')
def get_meters():
    db = "/home/egk/Pile/Coursera/w5/meters.db"
    meters = meters_from_db(db)
    return jsonify(meters)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
