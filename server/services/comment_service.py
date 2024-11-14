from server.models import Comment
# from server import db
# from sqlalchemy import func, literal
# from sqlalchemy.orm import aliased

# def get_comment_tree_for_post(post_id, limit, offset):
#     # Define a recursive query to get the comments, limiting depth
#     comment_tree = (
#         db.session.query(
#             Comment.id,
#             Comment.content,
#             Comment.created_at,
#             Comment.author_id,
#             Comment.parent_id,
#             Comment.post_id,
#             literal(1).label('depth'),
#             func.row_number().over(
#                 partition_by=Comment.parent_id,
#                 order_by=Comment.created_at
#             ).label('row_number')
#         )
#         .filter(Comment.post_id == post_id, Comment.parent_id == None)  # Filter by post_id and top-level comments
#         .limit(limit)   # Apply limit to top-level comments
#         .offset(offset) # Apply offset to top-level comments
#         .cte(name='comment_tree', recursive=True)
#     )

#     parent_comment = aliased(comment_tree)

#     # Recursive part to limit depth and count excess children
#     recursive_query = comment_tree.union_all(
#         db.session.query(
#             Comment.id,
#             Comment.content,
#             Comment.created_at,
#             Comment.author_id,
#             Comment.parent_id,
#             Comment.post_id,
#             (parent_comment.c.depth + 1).label('depth'),
#             func.row_number().over(
#                 partition_by=Comment.parent_id,
#                 order_by=Comment.created_at
#             ).label('row_number')
#         )
#         .filter(Comment.parent_id == parent_comment.c.id)
#         .filter(parent_comment.c.depth < 5)  # Limit depth to 5
#     )

#     # Subquery to get the count of extra children
#     extra_children_subquery = (
#         db.session.query(
#             func.count(Comment.id).label('extra_children'),
#             Comment.parent_id
#         )
#         .filter(Comment.parent_id == parent_comment.c.id)
#         .filter(func.row_number().over(partition_by=Comment.parent_id, order_by=Comment.created_at) > 5)  # Children beyond the 5th child
#         .group_by(Comment.parent_id)
#     ).subquery()

#     # Subquery to count extra depth beyond the 5th level
#     extra_depth_subquery = (
#         db.session.query(
#             func.count(Comment.id).label('extra_depth'),
#             Comment.parent_id
#         )
#         .filter(Comment.parent_id == parent_comment.c.id)
#         .filter(parent_comment.c.depth >= 5)  # Depths beyond the 5th level
#         .group_by(Comment.parent_id)
#     ).subquery()

#     # Join these counts with the recursive query
#     tree_query = (
#         db.session.query(
#             recursive_query,
#             extra_children_subquery.c.extra_children,
#             extra_depth_subquery.c.extra_depth
#         )
#         .outerjoin(extra_children_subquery, extra_children_subquery.c.parent_id == recursive_query.c.id)
#         .outerjoin(extra_depth_subquery, extra_depth_subquery.c.parent_id == recursive_query.c.id)
#         .order_by(recursive_query.c.created_at)
#     )

#     # Execute the query
#     comments = db.session.execute(tree_query).fetchall()

#     return comments

def get_comment_tree(comment_id, current_depth=1, max_depth=5):
    comment = Comment.query.get(comment_id)
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