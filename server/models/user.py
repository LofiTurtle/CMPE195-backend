from enum import Enum

from server import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    profile = db.relationship('UserProfile', uselist=False, back_populates='user')
    tokens = db.relationship('UserToken', back_populates='user')
    posts = db.relationship('Post', back_populates='author')
    liked_posts = db.relationship('Post', secondary='post_likes', back_populates='likes')
    comments = db.relationship('Comment', back_populates='author')
    liked_comments = db.relationship('Comment', secondary='comment_likes', back_populates='likes')
    communities = db.relationship('Community', secondary='user_communities', back_populates='users')

    def __init__(self, username, password):
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.profile = UserProfile()
        self.profile.bio = 'This is a default bio.'

    def set_password(self, password) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password) -> bool:
        return check_password_hash(self.password_hash, password)

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'id': self.id,
            'username': self.username,
            'profile': self.profile.serialize(),
        }


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bio = db.Column(db.String(1024), nullable=False)
    # TODO other profile information

    user = db.relationship('User', uselist=False, back_populates='profile')

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'bio': self.bio
        }


class OAuthProvider(Enum):
    """
    Supported providers for OAuth 2.0
    """
    DISCORD = 'discord'


class UserToken(db.Model):
    """
    Stores a token associated with a user for a 3rd party service
    """
    __tablename__ = 'user_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.Enum(OAuthProvider), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', uselist=False, back_populates='tokens')
