from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()

app = Flask(__name__)
app.config.from_pyfile('config.py')

db.init_app(app)

app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = True

jwt = JWTManager(app)

import server.routes

with app.app_context():
    db.create_all()

