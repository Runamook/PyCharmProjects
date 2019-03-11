from flask import Flask, jsonify, request, Response
from redis import Redis

app = Flask(__name__)
redis = Redis(host='redis', port=6379)

books = [
    {
        'name': 'Green eggs and Ham',
        'price': 7.99,
        'ISBN': 987654321
    },
    {
        'name': 'The cat in the Hat',
        'price': 5.99,
        'ISBN': 123456789
    }
]

# GET /books
@app.route('/books')
def get_books():
    return jsonify({'books': books})


# GET /books/<isbn>
@app.route('books/<int:isbn>')
def get_book_by_isbn(isbn):
    return_value = {}
    for book in books:
        if book['isbn'] == isbn:
            return_value = {
                'name': book['name'],
                'price': book['price']
            }
    return jsonify(return_value)


def validobject(bookobject):
    if 'name' in bookobject and 'price' in bookobject and 'isbn' in bookobject:
        return True
    else:
        return False


@app.route('/books', methods=['POST'])
def add_book():
    request_data = request.get_json()
    if validobject(request_data):
        new_book = {
            'name': request_data['name'],
            'price': request_data['price'],
            'isbn': request_data['price']
        }
        books.insert(0, new_book)
        response = Response('', 201, mimetype='application/json')
        response.headers['Location'] = '/books/' + str(new_book['isbn'])
        return response
    else:
        return 'False'


@app.route('/')
def hello():
    redis.incr('hits')
    return 'Hello World! I have been seen %s times.' % redis.get('hits')


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
