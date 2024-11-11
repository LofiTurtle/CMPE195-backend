import os
import shutil

import pytest
from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from server.models import db, User

TEST_USERNAME = 'test_user'
TEST_PASSWORD = '<PASSWORD>'

load_dotenv()


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.from_pyfile('../server/config.py')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Enable testing mode
    app.config['TESTING'] = True

    # Enable debug mode to get detailed errors
    app.config['DEBUG'] = True

    # Disable error catching during request handling
    app.config['PROPAGATE_EXCEPTIONS'] = True

    db.init_app(app)
    jwt = JWTManager(app)

    with app.app_context():
        db.create_all()

    from server.routes import api
    app.register_blueprint(api)

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()

    if os.path.exists(app.config['UPLOAD_DIRECTORY']):
        shutil.rmtree(app.config['UPLOAD_DIRECTORY'])


@pytest.fixture
def client(app):
    test_client = app.test_client()
    yield test_client


# Fixture to create a test user and get JWT token
@pytest.fixture
def auth_headers(app):
    with app.app_context():
        # Create a test user
        user = User(
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
        )
        db.session.add(user)
        db.session.commit()

        # Create access token
        access_token = create_access_token(identity=user.id)

        return {'Authorization': f'Bearer {access_token}'}
