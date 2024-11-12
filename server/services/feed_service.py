from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import text, desc, func
from typing import NamedTuple

from server import db
from server.models import Comment
from server.models.post import post_likes, Post, Community, user_communities
from server.models.user import user_following


class _SortFunction(NamedTuple):
    """Represents a sorting function for posts"""
    expression: str  # SQL expression
    extra_joins: list = []
    window_days: int = None


class SortType(Enum):
    NEW = 'new'
    TOP = 'top'
    HOT = 'hot'


def _new_sort() -> _SortFunction:
    score_expr = """
        post.created_at DESC
    """
    return _SortFunction(expression=score_expr)


def _top_sort() -> _SortFunction:
    score_expr = """
        COALESCE(likes_count, 0) DESC
    """
    return _SortFunction(expression=score_expr)


def _hot_sort() -> _SortFunction:
    """
    Sort by combination of age and popularity
    Similar to Reddit's hot algorithm
    """
    score_expr = """
        (LOG10(MAX(likes_count, 1)) * 2) - (POW((julianday('now') - julianday(post.created_at)) * 24, 1.8)) DESC
    """
    return _SortFunction(expression=score_expr)


def get_feed_posts(sort_type: str, current_user=None, community=None, user=None, start=0, limit=20):
    """
    :param sort_type: Type of sort for the feed
    :param current_user: Return posts for the current user's homepage - Mutually exclusive w/ community and user
    :param community: Return posts from a specific community - Mutually exclusive
    :param user: Return posts from a specific user - Mutually exclusive
    :param start: Not yet implemented
    :param limit: Maximum number of posts to return
    :return:
    """
    if sum((current_user is not None, community is not None, user is not None)) != 1:
        # Validate inputs
        raise ValueError("Exactly one of homepage, community_id, or user_id must be specified")

    if sort_type == SortType.NEW.value:
        sort_function = _new_sort()
    elif sort_type == SortType.TOP.value:
        sort_function = _top_sort()
    elif sort_type == SortType.HOT.value:
        sort_function = _hot_sort()
    else:
        raise ValueError(f'sort_type must be one of {[e.value for e in SortType]}')

    # Count post likes
    likes_count = db.select(
        post_likes.c.post_id,
        func.count(post_likes.c.user_id).label('likes_count')
    ).group_by(post_likes.c.post_id).subquery()

    # Count post comments
    comments_count = db.select(
        Comment.post_id,
        func.count(Comment.id).label('comment_count')
    ).group_by(Comment.post_id).subquery()

    # Base query object
    query = Post.query.join(Post.author).join(Post.community)

    query = query.outerjoin(likes_count, Post.id == likes_count.c.post_id)
    query = query.outerjoin(comments_count, Post.id == comments_count.c.post_id)

    for join_table, join_condition in sort_function.extra_joins:
        query = query.join(join_table, join_condition)

    if sort_function.window_days:
        window_start = datetime.now(timezone.utc) - timedelta(days=sort_function.window_days)
        query = query.filter(Post.created_at >= window_start)

    # Filter based on the feed type (homepage, community, or user)
    if current_user is not None:
        query = query.filter(
            db.or_(
                Community.id.in_(
                    db.select(Community.id)
                    .join(user_communities)
                    .where(user_communities.c.user_id == current_user.id)
                ),
                Post.author_id.in_(
                    db.select(user_following.c.followed_id)
                    .where(user_following.c.follower_id == current_user.id)
                )
            )
        )
    elif community is not None:
        query = query.filter(Community.id == community.id)
    elif user is not None:
        query = query.filter(Post.author_id == user.id)
    else:
        # Should never happen, but just in case
        raise ValueError("Must specify either homepage or community_id or user_id")

    # Sort according to the sort function
    query = query.group_by(
        Post,
        likes_count.c.likes_count,
        comments_count.c.comment_count
    ).order_by(text(sort_function.expression))

    return query.limit(limit).all()
