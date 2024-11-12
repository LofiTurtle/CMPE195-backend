from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from server.models import db

app = Flask(__name__)
app.config.from_pyfile('config.py')

db.init_app(app)

migrate = Migrate(app, db)

jwt = JWTManager(app)

from server.routes import api
app.register_blueprint(api)
