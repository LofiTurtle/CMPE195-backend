from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from server.models import db

app = Flask(__name__)
app.config.from_pyfile('config.py')

db.init_app(app)

jwt = JWTManager(app)

import server.routes

with app.app_context():
    db.create_all()
