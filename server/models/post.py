from datetime import datetime

from server import db


post_likes = db.Table('post_likes',
                      db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                      )

comment_likes = db.Table('comment_likes',
                         db.Column('comment_id', db.Integer, db.ForeignKey('comment.id')),
                         db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                         )

user_communities = db.Table('user_communities',
                            db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                            db.Column('community_id', db.Integer, db.ForeignKey('community.id'))
                            )


class Community(db.Model):
    """
    Represents a community for a game. Analogous to a subreddit
    """
    __tablename__ = 'community'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    posts = db.relationship('Post', back_populates='community')
    users = db.relationship('User', secondary=user_communities, back_populates='communities')

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'id': self.id,
            'name': self.name,
            'num_users': len(self.users)
        }


class Post(db.Model):
    """
    Represents a post within a game community.
    """
    __tablename__ = 'post'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    community = db.relationship('Community', back_populates='posts')
    author = db.relationship('User', back_populates='posts', uselist=False)
    comments = db.relationship('Comment', back_populates='post')
    likes = db.relationship('User', secondary=post_likes, back_populates='liked_posts')

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'community': self.community.serialize(),
            'author': self.author.serialize(),
            'comments': [comment.serialize() for comment in self.comments],
            'num_likes': len(self.likes)
        }
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', content='{self.content[:20]}...', community_id={self.community_id}, author_id={self.author_id})>"


class Comment(db.Model):
    """
    Represents a comment on a post.
    """
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

    author = db.relationship('User', back_populates='comments', uselist=False)
    post = db.relationship('Post', back_populates='comments', uselist=False)
    likes = db.relationship('User', secondary=comment_likes, back_populates='liked_comments')

    def serialize(self):
        """Return object data in JSON format"""
        return {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author_id': self.author.id,
            'post_id': self.post_id,
            'num_likes': len(self.likes)
        }
    

    def __repr__(self):
        return f"<Comment(id={self.id}, content={self.content}, post_id={self.post_id}, author_id={self.author_id})>"
