import io
import os
import shutil

import pytest
from PIL import Image
from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.orm import scoped_session

from server.models import db, User, IgdbGame, Community, Post
from server import app as global_app

TEST_USERNAME = 'test_user'
TEST_PASSWORD = '<PASSWORD>'

load_dotenv()
load_dotenv('../.flaskenv')


@pytest.fixture(scope='session')
def app():
    app = Flask(__name__)
    app.config.from_pyfile('../server/config.py')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True

    global_app.config = app.config

    db.init_app(app)
    jwt = JWTManager(app)

    from server.routes import api
    app.register_blueprint(api)

    yield app

    if os.path.exists(app.config['UPLOAD_DIRECTORY']):
        shutil.rmtree(app.config['UPLOAD_DIRECTORY'])


@pytest.fixture(scope='function')
def db_session(app):
    """Create a fresh database session for each test."""
    with app.app_context():
        db.create_all()
        session = scoped_session(db.session.registry)
        yield session
        session.remove()
        db.drop_all()


@pytest.fixture
def test_user(db_session):
    """Create a test user that stays attached to the session."""
    user = User(username=TEST_USERNAME, password=TEST_PASSWORD)
    db_session.add(user)
    db_session.commit()

    # Return the user directly from the session to ensure it's attached
    return db_session.get(User, user.id)


@pytest.fixture
def auth_headers(app, test_user):
    """Create authentication headers for the test user."""
    with app.app_context():
        access_token = create_access_token(identity=test_user.id)
        return {'Authorization': f'Bearer {access_token}'}


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_game(app, db_session):
    """Create a test game for the community"""
    with app.app_context():
        game = IgdbGame(
            name="Test Game",
            cover="test_cover",
            artwork="test_artwork",
            summary="A test game for testing communities"
        )
        db_session.add(game)
        db_session.commit()
        return db_session.get(IgdbGame, game.id)


@pytest.fixture
def test_community(app, test_user, test_game, db_session):
    """Create a test community"""
    with app.app_context():
        community = Community(
            name="Test Community",
            igbd_id=test_game.id,
            owner_id=test_user.id
        )
        db_session.add(community)
        db_session.commit()
        return db_session.get(Community, community.id)


@pytest.fixture
def test_post(app, test_user, test_community, db_session):
    """Create a test post"""
    with app.app_context():
        post = Post(
            title="Test Post",
            content="Test content for the post",
            community_id=test_community.id,
            author_id=test_user.id
        )
        db_session.add(post)
        db_session.commit()
        return db_session.get(Post, post.id)


@pytest.fixture
def test_post_with_image(app, test_user, test_community, db_session):
    """Create a test post with an image"""
    with app.app_context():
        post = Post(
            title="Test Post with Image",
            content="Test content with image",
            community_id=test_community.id,
            author_id=test_user.id,
            image_id="test-image-id"
        )

        # Create a test image file
        image_path = os.path.join(app.config['UPLOAD_DIRECTORY'], 'test-image-id.jpg')
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image_path)

        db_session.add(post)
        db_session.commit()
        return db_session.get(Post, post.id)


@pytest.fixture
def mock_igdb_game_data():
    return {
        'id': 123,
        'name': 'Test Game',
        'cover': {'url': '/test_cover.jpg'},
        'artworks': [{'url': '/test_artwork.jpg'}],
        'summary': 'A test game',
        'first_release_date': 1577836800  # 2020-01-01
    }


@pytest.fixture
def mock_igdb_search_response():
    """Mock response from IGDB API"""
    return [
        {
            'id': 123,
            'name': 'Test Game',
            'cover': {'url': '//images.igdb.com/test.jpg'},
            'summary': 'A test game',
            'first_release_date': 1577836800
        }
    ]


def create_test_image(size=100):
    file = io.BytesIO()
    Image.new('RGB', (size, size), color='red').save(file, 'JPEG')
    file.seek(0)
    return file
