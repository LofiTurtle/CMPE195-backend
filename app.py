from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route('/api/hello')
def api_hello():
    return jsonify(data='Hello from the flask API')


if __name__ == '__main__':
    app.run()
