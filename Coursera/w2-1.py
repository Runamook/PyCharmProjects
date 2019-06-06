import os
import tempfile
import argparse
import json


parser = argparse.ArgumentParser()
parser.add_argument("--key", help="Key name")
parser.add_argument("--value", help="Value")
args = parser.parse_args()

if args.key:
    key = args.key
elif not args.key:
    raise KeyError

if args.value:
    val = args.value
else:
    val = None

# storage_path = "f.txt"
storage_path = os.path.join(tempfile.gettempdir(), 'storage.data')

if val is not None:
    # Writing K-V
    if os.path.exists(storage_path) and int(os.path.getsize(storage_path)) > 0:
        with open(storage_path, "r") as f:
            data = json.load(f)
        with open(storage_path, "w") as f:
            if key in data:
                data[key].append(val)
            elif key not in data:
                data[key] = [val]
            json.dump(data, f)

    else:
        mode = "w"
        data = dict()
        data[key] = [val]
        try:
            f = open(storage_path, mode)
            json.dump(data, f)
        finally:
            f.close()

elif val is None:
    # Reading K-V
    with open(storage_path, 'r') as f:
        result = json.load(f)
        i = len(result[key])
        for value in result[key]:
            if i > 1:
                print(value, end=", ")
            elif i == 1:
                print(value)
            i -= 1
