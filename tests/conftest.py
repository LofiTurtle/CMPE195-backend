import io
import os
import shutil
from datetime import timedelta, datetime

import pytest
from PIL import Image
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token

from server import create_app, db
from server.models import User, IgdbGame, Community, Post, Comment

TEST_USERNAME = 'test_user'
TEST_PASSWORD = '<PASSWORD>'

load_dotenv()
load_dotenv('../.flaskenv')


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    test_config = {
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True,
        'DEBUG': True,
        'PROPAGATE_EXCEPTIONS': True
    }

    _app = create_app(test_config)

    with _app.app_context():
        db.create_all()
        yield _app
        db.drop_all()

        # if os.path.exists(_app.config['UPLOAD_DIRECTORY']):
        #     shutil.rmtree(_app.config['UPLOAD_DIRECTORY'])


@pytest.fixture(autouse=True)
def db_transaction(app):
    """Create a fresh transaction for each test."""
    with app.app_context():
        db.create_all()
        yield
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    user = User(username=TEST_USERNAME, password=TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_user_with_profile_picture(app, test_user):
    """Create a test user with a profile picture."""
    test_user.profile.profile_picture_id = 'pfp_id'

    # Create the test profile picture
    image_path = os.path.join(app.config['UPLOAD_DIRECTORY'], 'pfp_id.jpg')
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    img = Image.new('RGB', (100, 100), color='red')
    img.save(image_path)

    db.session.add(test_user)
    db.session.commit()

    yield test_user

    if os.path.exists(image_path):
        os.remove(image_path)


@pytest.fixture
def auth_headers(app, test_user):
    """Create authentication headers for the test user."""
    with app.app_context():
        access_token = create_access_token(identity=str(test_user.id))
        return {'Authorization': f'Bearer {access_token}'}


@pytest.fixture
def test_game(app):
    """Create a test game for the community"""
    game = IgdbGame(
        name="Test Game",
        cover="test_cover",
        artwork="test_artwork",
        summary="A test game for testing communities"
    )
    db.session.add(game)
    db.session.commit()
    return game


@pytest.fixture
def test_community(app, test_user, test_game):
    """Create a test community"""
    community = Community(
        name="Test Community",
        igbd_id=test_game.id,
        owner_id=test_user.id
    )
    db.session.add(community)
    db.session.commit()
    return community


@pytest.fixture
def test_post(app, test_user, test_community):
    """Create a test post"""
    post = Post(
        title="Test Post",
        content="Test content for the post",
        community_id=test_community.id,
        author_id=test_user.id
    )
    db.session.add(post)
    db.session.commit()
    return post


@pytest.fixture
def test_post_with_image(app, test_user, test_community):
    """Create a test post with an image"""
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

    db.session.add(post)
    db.session.commit()
    yield post
    if os.path.exists(image_path):
        os.remove(image_path)


@pytest.fixture
def test_post_with_comments(app, test_user, test_post):
    base_time = datetime.now() - timedelta(days=1)
    comment_group = [
        Comment(id=4, content='Top-level comment 1',
                created_at=base_time + timedelta(hours=14),
                updated_at=base_time + timedelta(hours=14),
                author=test_user, post=test_post),
        Comment(id=5, content='Top-level comment 2',
                created_at=base_time + timedelta(hours=15),
                updated_at=base_time + timedelta(hours=15),
                author=test_user, post=test_post),
        Comment(id=6, content='Reply to comment 1',
                created_at=base_time + timedelta(hours=16),
                updated_at=base_time + timedelta(hours=16),
                author=test_user, parent_id=4, post=test_post),
        Comment(id=7, content='Another reply to comment 1',
                created_at=base_time + timedelta(hours=17),
                updated_at=base_time + timedelta(hours=17),
                author=test_user, parent_id=4, post=test_post),
        Comment(id=8, content='Reply to reply 3',
                created_at=base_time + timedelta(hours=18),
                updated_at=base_time + timedelta(hours=18),
                author=test_user, parent_id=6, post=test_post),
        Comment(id=9, content='Another reply to reply 3',
                created_at=base_time + timedelta(hours=19),
                updated_at=base_time + timedelta(hours=19),
                author=test_user, parent_id=6, post=test_post),
        Comment(id=10, content='Reply to comment 2',
                created_at=base_time + timedelta(hours=20),
                updated_at=base_time + timedelta(hours=20),
                author=test_user, parent_id=5, post=test_post),
        Comment(id=11, content='Reply to reply 7',
                created_at=base_time + timedelta(hours=21),
                updated_at=base_time + timedelta(hours=21),
                author=test_user, parent_id=7, post=test_post),
        Comment(id=12, content='Another reply to reply 7',
                created_at=base_time + timedelta(hours=22),
                updated_at=base_time + timedelta(hours=22),
                author=test_user, parent_id=7, post=test_post),
        Comment(id=13, content='Reply to 12',
                created_at=base_time + timedelta(hours=23),
                updated_at=base_time + timedelta(hours=23),
                author=test_user, parent_id=12, post=test_post),
        Comment(id=14, content='Reply to 13',
                created_at=base_time + timedelta(hours=24),
                updated_at=base_time + timedelta(hours=24),
                author=test_user, parent_id=13, post=test_post),
        Comment(id=15, content='Reply to 14',
                created_at=base_time + timedelta(hours=25),
                updated_at=base_time + timedelta(hours=25),
                author=test_user, parent_id=14, post=test_post),
        Comment(id=16, content='Reply to 15',
                created_at=base_time + timedelta(hours=26),
                updated_at=base_time + timedelta(hours=26),
                author=test_user, parent_id=15, post=test_post)
    ]
    db.session.add_all(comment_group)
    db.session.commit()
    return test_post


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
