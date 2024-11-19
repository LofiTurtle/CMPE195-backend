import os

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

jwt = JWTManager()


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    if config is not None:
        app.config.update(config)

    db.init_app(app)
    jwt.init_app(app)

    migrate = Migrate(app, db)

    from server.routes import api

    app.register_blueprint(api)

    if os.getenv('FLASK_ENV') == 'development':
        from server.development import dev

        app.register_blueprint(dev)
    return app


app = create_app()
