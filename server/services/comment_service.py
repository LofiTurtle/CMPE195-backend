from server import db
from server.models import Comment


def get_comment_tree(comment_id, current_depth=1, max_depth=5):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return None

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
        'replies': [get_comment_tree(reply.id, current_depth + 1, max_depth) for reply in replies]
    }