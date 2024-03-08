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

    def __init__(self, username, password):
        self.username = username
        self.password_hash = generate_password_hash(password)

    def set_password(self, password) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password) -> bool:
        return check_password_hash(self.password_hash, password)


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # TODO other profile information

    user = db.relationship('User', uselist=False, back_populates='profile')


class OAuthProvider(Enum):
    DISCORD = 'discord'
    STEAM = 'steam'


class UserToken(db.Model):
    __tablename__ = 'user_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.Enum(OAuthProvider), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', uselist=False, back_populates='tokens')
