from server import db
from server.models import Comment, comment_likes
from sqlalchemy import exists

def get_comment_tree(comment_id, current_user_id=None, current_depth=1, max_depth=5):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return None

    # Check if the current user has liked this comment
    liked_by_current_user = False
    if current_user_id:
        liked_by_current_user = db.session.query(
            exists().where(
                (comment_likes.c.comment_id == comment_id) &
                (comment_likes.c.user_id == current_user_id)
            )
        ).scalar()

    if current_depth > max_depth:
        return {
            'id': comment.id,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'updated_at': comment.updated_at.isoformat(),
            'author': comment.author.serialize() if comment.author else None,
            'parent_id': comment.parent_id,
            'post_id': comment.post_id,
            'num_likes': len(comment.likes),
            'liked_by_current_user': liked_by_current_user,
            'replies': []
        }

    replies = Comment.query.filter_by(parent_id=comment_id).all()

    return {
        'id': comment.id,
        'content': comment.content,
        'created_at': comment.created_at.isoformat(),
        'updated_at': comment.updated_at.isoformat(),
        'author': comment.author.serialize() if comment.author else None,
        'parent_id': comment.parent_id,
        'post_id': comment.post_id,
        'num_likes': len(comment.likes),
        'liked_by_current_user': liked_by_current_user,
        'replies': [
            get_comment_tree(reply.id, current_user_id, current_depth + 1, max_depth)
            for reply in replies
        ]
    }
