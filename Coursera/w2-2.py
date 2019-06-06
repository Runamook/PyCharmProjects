import json
import functools


def to_json(func):
    @functools.wraps(func)
    def wrapper():
        return json.dumps(func())
    return wrapper


@to_json
def get_data():
    return {'data': 42}


get_data()  # вернёт '{"data": 42}'
