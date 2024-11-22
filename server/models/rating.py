from datetime import datetime, timezone
from enum import Enum

from server import db


class Rating(db.Model):
    __tablename__ = 'rating'

    id = db.Column(db.Integer, primary_key=True)
    rating_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rated_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    rating_user = db.relationship('User', back_populates='given_ratings', foreign_keys=rating_user_id, uselist=False)
    rated_user = db.relationship('User', back_populates='received_ratings', foreign_keys=rated_user_id, uselist=False)
    fields = db.relationship('RatingField', back_populates='rating')

    def serialize(self):
        return {
            'id': self.id,
            'rating_user_id': self.rating_user_id,
            'rated_user_id': self.rated_user_id,
            'fields': [field.serialize() for field in self.fields],
            'description': self.description,
            'created_at': self.created_at
        }


class RatingFieldName(Enum):
    ATTITUDE = 'attitude'
    COMMUNICATION = 'communication'
    RELIABILITY = 'reliability'
    TEAMWORK = 'teamwork'


class RatingField(db.Model):
    __tablename__ = 'rating_field'

    id = db.Column(db.Integer, primary_key=True)
    rating_id = db.Column(db.Integer, db.ForeignKey('rating.id'), nullable=False)
    name = db.Column(db.Enum(RatingFieldName), nullable=False)
    value = db.Column(db.Integer, nullable=False)

    rating = db.relationship('Rating', back_populates='fields', uselist=False)

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'value': self.value
        }