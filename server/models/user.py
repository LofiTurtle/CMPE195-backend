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
    connected_accounts = db.relationship('ConnectedAccount', back_populates='user')
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
            'follower_count': len(self.followers),
            'following_count': len(self.following),
            'communities_count': len(self.communities),
            'connected_accounts': [account.serialize() for account in self.connected_accounts],
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


class ConnectedService(Enum):
    """
    Supported 3rd party account providers, also used as provider's display name
    """
    DISCORD = 'Discord'
    STEAM = 'Steam'


# TODO separate this into dedicated tables for each service, or expand this table to support more things
#  e.g. display names
#  atm, only Discord is supported
class ConnectedAccount(db.Model):
    """Stores connected accounts for a user"""
    __tablename__ = 'connected_account'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(128), nullable=False)
    discord_user_id = db.Column(db.String(128), nullable=True)
    profile_picture = db.Column(db.String(), nullable=True)
    provider = db.Column(db.Enum(ConnectedService), nullable=False)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', uselist=False, back_populates='connected_accounts')

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'username': self.username,
            'discord_user_id': self.discord_user_id,
            'profile_picture_url': f'https://cdn.discordapp.com/avatars/{self.discord_user_id}/{self.profile_picture}.png',  # TODO see if this breaks for .gif pfps
            'provider': self.provider.value
        }

# TODO store gameplay history and other info related to ConnectedAccount
