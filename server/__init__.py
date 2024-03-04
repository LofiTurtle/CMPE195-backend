from flask import Flask


app = Flask(__name__)

# Configuration
app.config.from_pyfile('config.py')

import server.routes
