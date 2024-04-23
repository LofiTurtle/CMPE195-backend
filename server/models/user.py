from enum import Enum
from operator import index

from server import db
from werkzeug.security import generate_password_hash, check_password_hash


user_following = db.Table('user_following',
                          db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                          db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
                          )


class User(db.Model):
    """
    Model for general account information for a user.
    """

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
    following = db.relationship(
        'User',
        secondary=user_following,
        primaryjoin=(id == user_following.c.follower_id),
        secondaryjoin=(id == user_following.c.followed_id),
        back_populates='followers'
    )
    followers = db.relationship(
        'User',
        secondary=user_following,
        primaryjoin=(id == user_following.c.followed_id),
        secondaryjoin=(id == user_following.c.follower_id),
        back_populates='following'
    )

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
    """
    Model for information about a user's profile.
    """

    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bio = db.Column(db.String(1024), nullable=False)
    profile_picture_id = db.Column(db.String(36), nullable=True)
    # TODO other profile information

    user = db.relationship('User', uselist=False, back_populates='profile')

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'bio': self.bio
        }


class InvalidatedToken(db.Model):
    """Stores invalidated JWT tokens, e.g. for when a user logs out"""
    __tablename__ = 'invalidated_token'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.String(36), nullable=False, index=True)
    expired_at = db.Column(db.DateTime, nullable=False)


class OAuthProvider(Enum):
    """
    Supported providers for OAuth 2.0
    """
    DISCORD = 'discord'


class UserToken(db.Model):
    """
    Stores a user's access and refresh tokens for an OAuth provider.
    """
    __tablename__ = 'user_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.Enum(OAuthProvider), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', uselist=False, back_populates='tokens')
