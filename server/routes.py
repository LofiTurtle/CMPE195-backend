import os
from datetime import datetime, timedelta
from operator import or_

import requests
from flask import jsonify, request, redirect, send_file, render_template, Blueprint, current_app
from flask_jwt_extended import create_access_token, jwt_required, \
    get_jwt_identity, set_access_cookies, get_jwt, unset_access_cookies
from sqlalchemy.exc import IntegrityError

from server import db, jwt
from server.models import User, Post, Comment, InvalidatedToken, Community, ConnectedService, ConnectedAccount, \
    IgdbGame, Rating, RatingField, RatingFieldName
from server.services import fetch_discord_account_data, validate_password
from server.services.feed_service import get_feed_posts, SortType
from server.services.games_service import search_igdb_games, get_game, IGDBError, api_response_to_model
from server.services.media_processing import save_image, delete_image
from server.services.comment_service import get_comment_tree

api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/register', methods=['POST'])
def register():
    """
    Creates a new user account. Accepts JSON payload with `username` and `password` fields.
    :return: Access token and refresh token on successful account creation, or error message on failure, indicated by
    the `success` field.
    """
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username is None or password is None:
        return jsonify(success=False, msg='Username or password not provided'), 400

    user = User.query.filter_by(username=username).first()
    if user is not None:
        return jsonify(success=False, msg='Username already taken'), 409

    if not validate_password(password):
        return jsonify(success=False, msg='Invalid password'), 400

    user = User(username, password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id), fresh=True)
    response = jsonify(success=True, msg='User created successfully')
    set_access_cookies(response, access_token)
    return response, 201


@api.route('/login', methods=['POST'])
def login():
    """
    Logs in an existing user. Accepts JSON payload with `username` and `password` fields.
    :return: Access token and refresh token on successful authentication, indicated by the `success` field.
    """
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username is None or password is None:
        return jsonify(success=False, msg='Username or password not provided'), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify(success=False, msg='Invalid username or password'), 401

    access_token = create_access_token(identity=str(user.id), fresh=True)
    response = jsonify(success=True, msg='Logged in successfully')
    set_access_cookies(response, access_token)
    return response, 200


@jwt.token_in_blocklist_loader
def is_token_revoked(jwt_headers, jwt_payload):
    """Checks if the token is revoked."""
    jti = jwt_payload['jti']
    token = db.session.query(InvalidatedToken).filter_by(token_id=jti).first()
    return token is not None


@api.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logs a user out, removing the access token cookie and revoking the token."""
    token = get_jwt()
    db.session.add(InvalidatedToken(token_id=token['jti'], expired_at=datetime.fromtimestamp(token['exp'])))
    db.session.commit()
    response = jsonify(msg='Logged out successfully')
    unset_access_cookies(response)
    return response, 200


@api.route('/me', methods=['GET'])
@jwt_required()
def me():
    """
    :return: Information about the current user
    """
    identity = get_jwt_identity()
    user = User.query.filter_by(id=identity).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(user=user.serialize())


@api.route('/me', methods=['PUT'])
@jwt_required()
def edit_profile():
    """Takes username, bio, password, and profile_picture as form data"""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg='User not found'), 404

    username = request.form.get('username', None)
    bio = request.form.get('bio', None)
    profile_picture = request.files.get('profile_picture', None)
    newPassword = request.form.get('password')

    if bio:
        user.profile.bio = bio
    if profile_picture and profile_picture.filename != '':
        pfp_uuid = save_image(profile_picture)
        delete_image(user.profile.profile_picture_id)
        user.profile.profile_picture_id = pfp_uuid
    if username:
        user.username = username
    if newPassword:
        print(newPassword)
        user.set_password(newPassword)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        return jsonify(msg='Username already taken'), 409

    return jsonify(user=user.serialize())


@api.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify(users=[user.serialize() for user in users])


@api.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(user=user.serialize())


@api.route('/users/<int:user_id>/profile-picture', methods=['GET'])
def get_user_profile_picture(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg='User not found'), 404
    filepath = os.path.abspath(os.path.join(current_app.config['UPLOAD_DIRECTORY'], f'{user.profile.profile_picture_id}.jpg'))
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    else:
        default_profile_filepath = os.path.abspath(os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'default-profile.png'))
        return send_file(default_profile_filepath, mimetype='image/png')


@api.route('/users/<int:user_id>/followers', methods=['GET'])
def get_followers(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(users=[follower.serialize() for follower in user.followers])


@api.route('/users/<int:user_id>/following', methods=['GET'])
def get_following(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(users=[following_user.serialize() for following_user in user.following])


@api.route('/users/<int:target_user_id>/follow', methods=['POST'])
@jwt_required()
def follow(target_user_id):
    current_user = User.query.filter_by(id=get_jwt_identity()).first()
    if not current_user:
        return jsonify(msg='Logged in user not found'), 404

    target_user = User.query.filter_by(id=target_user_id).first()
    if not target_user:
        return jsonify(msg='User not found'), 404

    if current_user.id == target_user.id:
        return jsonify(msg='You cannot follow yourself'), 403

    if target_user in current_user.following:
        return '', 204

    current_user.following.append(target_user)
    db.session.commit()

    return '', 201


@api.route('/users/<int:target_user_id>/follow', methods=['DELETE'])
@jwt_required()
def unfollow(target_user_id):
    current_user = User.query.filter_by(id=get_jwt_identity()).first()
    if not current_user:
        return jsonify(msg='Logged in user not found'), 404

    target_user = User.query.filter_by(id=target_user_id).first()
    if not target_user:
        return jsonify(msg='User not found'), 404

    if current_user.id == target_user.id:
        return jsonify(msg='You cannot unfollow yourself'), 403

    if target_user not in current_user.following:
        return '', 204

    current_user.following.remove(target_user)
    db.session.commit()

    return '', 204


@api.route('/users/<int:target_user_id>/relationship', methods=['GET'])
@jwt_required()
def get_relationship(target_user_id):
    """Get the following/followed-by relationship between the current and target users"""
    current_user = User.query.filter_by(id=get_jwt_identity()).first()
    if not current_user:
        return jsonify(msg='Logged in user not found'), 404

    target_user = User.query.filter_by(id=target_user_id).first()
    if not target_user:
        return jsonify(msg='User not found'), 404

    return jsonify(following=target_user in current_user.following,
                   followed_by=target_user in current_user.followers)


@api.route('/users/<int:user_id>/communities', methods=['GET'])
def get_user_communities(user_id):
    """Get the communities a user follows"""
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404

    return jsonify(communities=[community.serialize() for community in user.communities])


@api.route('/communities/<int:community_id>/users', methods=['GET'])
def get_community_users(community_id):
    """Get the users who follow a community"""
    community = Community.query.filter_by(id=community_id).first()
    if not community:
        return jsonify(msg='Community not found'), 404

    return jsonify(users=[user.serialize() for user in community.users])


@api.route('/communities/<int:community_id>/follow', methods=['POST'])
@jwt_required()
def follow_community(community_id):
    current_user = User.query.filter_by(id=get_jwt_identity()).first()
    if not current_user:
        return jsonify(msg='Logged in user not found'), 404

    community = Community.query.filter_by(id=community_id).first()
    if not community:
        return jsonify(msg='Community not found'), 404

    if community in current_user.communities:
        return '', 204

    current_user.communities.append(community)
    db.session.commit()

    return '', 201


@api.route('/communities/<int:community_id>/follow', methods=['DELETE'])
@jwt_required()
def unfollow_community(community_id):
    current_user = User.query.filter_by(id=get_jwt_identity()).first()
    if not current_user:
        return jsonify(msg='Logged in user not found'), 404

    community = Community.query.filter_by(id=community_id).first()
    if not community:
        return jsonify(msg='Community not found'), 404

    if community not in current_user.communities:
        return '', 204

    current_user.communities.remove(community)
    db.session.commit()

    return '', 204


@api.route('/edit-profile-test', methods=['GET'])
def edit_profile_test():
    # TODO remove this after profile editing is implemented
    return render_template('edit_profile.html')


@api.route('/game-info/<int:game_id>', methods=['GET'])
def game_info(game_id):
    try:
        game = get_game(game_id)
        igdb_game = api_response_to_model(game)
        return jsonify(game=igdb_game.serialize())
    except IGDBError:
        return jsonify(msg='Game not found'), 404


@api.route('/communities', methods=['POST'])
@jwt_required()
def create_community():
    current_user = User.query.filter_by(id=get_jwt_identity()).first()
    if not current_user:
        return jsonify(msg='Logged in user not found'), 404

    game_id = request.json.get('game_id', None)
    community_name = request.json.get('community_name', None)

    if not game_id:
        return jsonify(msg='Game not found'), 404

    if not community_name:
        return jsonify(msg='Community name not provided'), 400

    game = get_game(game_id)

    igdb_game = api_response_to_model(game)

    community = Community(name=community_name, game=igdb_game, owner=current_user)

    db.session.add(community)

    # Make user follow their new community by default
    current_user.communities.append(community)

    db.session.commit()
    return jsonify(community=community.serialize()), 201


@api.route('/communities', methods=['GET'])
def get_communities():
    communities = Community.query.all()
    return jsonify(communities=[community.serialize() for community in communities])


@api.route('/communities/<int:community_id>', methods=['GET'])
def get_community(community_id):
    community = db.session.get(Community, community_id)
    if not community:
        return jsonify(msg='Community not found'), 404
    return jsonify(community=community.serialize())


def validate_sort_type(sort_type: str) -> tuple[str, bool]:
    if sort_type is None:
        # Default to 'hot' sorting
        sort_type = SortType.HOT.value
    try:
        SortType(sort_type)
        valid = True
    except ValueError:
        valid = False
    return sort_type, valid


@api.route('/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    sort_type, valid = validate_sort_type(request.args.get('sort'))
    if not valid:
        return jsonify(msg=f'Invalid sort type: {sort_type}'), 400
    user_posts = get_feed_posts(sort_type, user=user)
    return jsonify(posts=[post.serialize() for post in user_posts])


@api.route('/communities/<int:community_id>/posts', methods=['GET'])
def get_community_posts(community_id):
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', default=10, type=int)
    community = db.session.get(Community, community_id)
    if not community:
        return jsonify(msg='Community not found'), 404
    sort_type, valid = validate_sort_type(request.args.get('sort'))
    if not valid:
        return jsonify(msg=f'Invalid sort type: {sort_type}'), 400
    community_posts = get_feed_posts(sort_type, community=community)
    return jsonify(posts=[post.serialize() for post in community_posts])


@api.route('/homepage', methods=['GET'])
@jwt_required()
def homepage():
    """
    :return: Posts for this user's homepage
    """
    user = User.query.filter_by(id=get_jwt_identity()).first()
    sort_type, valid = validate_sort_type(request.args.get('sort'))
    if not valid:
        return jsonify(msg=f'Invalid sort type: {sort_type}'), 400

    homepage_posts = get_feed_posts(sort_type, current_user=user)
    return jsonify(posts=[post.serialize() for post in homepage_posts])


@api.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """
    :return: The post with the given ID
    """
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify(msg='Post not found'), 404
    return jsonify(post=post.serialize())


@api.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    title = request.form.get('title', None)
    content = request.form.get('content', None)
    community_id = request.form.get('community_id', None)
    author_id = get_jwt_identity()
    image = request.files.get('image', None)

    if title is None or content is None or community_id is None:
        return jsonify(success=False, msg='Incomplete post'), 400

    post = Post(
        title=title,
        content=content,
        community_id=community_id,
        author_id=author_id
    )

    if image:
        image_uuid = save_image(image)
        post.image_id = image_uuid

    current_app.logger.info(post)
    db.session.add(post)
    db.session.commit()

    response = jsonify(post=post.serialize())
    return response, 201


@api.route('/posts/<int:post_id>/image', methods=['GET'])
def get_post_image(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify(msg='Post not found'), 404
    if post.image_id is None:
        return jsonify(msg='Post has no associated image'), 404
    filepath = os.path.abspath(os.path.join(current_app.config['UPLOAD_DIRECTORY'], post.image_id + '.jpg'))
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    else:
        return jsonify(msg=f'Image for post with ID "{post_id}" not found'), 404


@api.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', default=10, type=int)

    max_depth = 5

    top_level_comments = (db.session.query(Comment).filter_by(post_id=post_id, parent_id=None)
                          .order_by(Comment.created_at)
                          .limit(limit)
                          .offset(offset)
                          .all())

    comments_tree = [get_comment_tree(comment.id, max_depth=max_depth) for comment in top_level_comments]

    return jsonify(comments_tree)


@api.route('/comments', methods=['POST'])
@jwt_required()
def create_comment():
    content = request.json.get('content', None)
    parent_id = request.json.get('parent_id', None)
    author_id = get_jwt_identity()
    post_id = request.json.get('post_id', None)

    if content is None or author_id is None or post_id is None:
        return jsonify(success=False, msgg='Incomplete comment'), 400

    current_user = db.session.get(User, author_id)
    if not current_user:
        return jsonify(success=False, msg='User not found'), 400

    else:
        comment = Comment(
            content=content,
            parent_id=parent_id,
            author=current_user,
            post_id=post_id
        )
        db.session.add(comment)
        db.session.commit()

    response = jsonify(comment=comment.serialize())
    return response, 201


@api.route('/linked-accounts', methods=['GET'], defaults={'user_id': None})
@api.route('/linked-accounts/<string:user_id>', methods=['GET'])
@jwt_required()
def get_linked_accounts(user_id):
    if user_id is None:
        # TODO use session to get current user ID
        pass

    return jsonify({
        'discord': fetch_discord_account_data(user_id),
        'steam': None
    })


@api.route('/search/communities', methods=['GET'])
def search_communities():
    query = request.args.get('q')
    if not query:
        return jsonify(msg='Search query is required'), 400

    communities = Community.query.join(Community.game).filter(
        or_(
            Community.name.ilike(f'%{query}%'),
            IgdbGame.name.ilike(f'%{query}%'),
        )
    ).all()

    return jsonify(communities=[community.serialize() for community in communities])


@api.route('/search/users', methods=['GET'])
def search_users():
    query = request.args.get('q')
    if not query:
        return jsonify(msg='Search query is required'), 400

    users = User.query.filter(User.username.ilike(f'%{query}%')).all()

    return jsonify(users=[user.serialize() for user in users])


@api.route('/search/games', methods=['GET'])
def search_games():
    search_term = request.args.get('q')
    if search_term is None:
        return jsonify(msg='No search term provided'), 400

    try:
        games = search_igdb_games(search_term)
    except IGDBError:
        return jsonify(msg='IGDB API Error'), 404
    igdb_games = []
    for game in games:
        igdb_games.append(api_response_to_model(game))

    return jsonify(games=[game.serialize() for game in igdb_games])


@api.route('/discord/connect')
@jwt_required()
def discord_connect():
    params = {
        'client_id': current_app.config['DISCORD_CLIENT_ID'],
        'redirect_uri': current_app.config['DISCORD_REDIRECT_URI'],
        'response_type': 'code',
        'scope': ' '.join(current_app.config['DISCORD_SCOPES'])
    }
    authorization_url = current_app.config['DISCORD_AUTH_URL'] + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])
    return redirect(authorization_url)


@api.route('/discord/callback')
@jwt_required()
def discord_callback():
    code = request.args.get('code')
    data = {
        'client_id': current_app.config['DISCORD_CLIENT_ID'],
        'client_secret': current_app.config['DISCORD_CLIENT_SECRET'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': current_app.config['DISCORD_REDIRECT_URI']
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(current_app.config['DISCORD_TOKEN_URL'], data=data, headers=headers)
    token_data = response.json()

    # TODO save token to database & fetch initial info

    access_token = token_data.get('access_token', None)
    refresh_token = token_data.get('refresh_token', None)
    expires_in = token_data.get('expires_in', None)
    if access_token is None or refresh_token is None or expires_in is None:
        return jsonify(success=False, msg='Invalid authorization code'), 400
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify(msg='User not found'), 401

    connected_discord_account = next(
        (account for account in user.connected_accounts if account.provider == ConnectedService.DISCORD), None)
    if connected_discord_account:
        connected_discord_account.access_token = access_token
        connected_discord_account.refresh_token = refresh_token
        connected_discord_account.expires_at = expires_at
    else:
        user.connected_accounts.append(ConnectedAccount(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            username='',
            provider=ConnectedService.DISCORD
        ))

    db.session.add(user)
    db.session.commit()

    fetch_discord_account_data(user.id)

    # redirect to user's account page
    return redirect(f'{current_app.config["REACT_APP_URL"]}/users/{get_jwt_identity()}')


@api.route('/discord/disconnect', methods=['POST'])
@jwt_required()
def discord_disconnect():
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify(msg='User not found'), 401

    connected_discord_account = next(
        (account for account in user.connected_accounts if account.provider == ConnectedService.DISCORD), None)
    if connected_discord_account:
        user.connected_accounts.remove(connected_discord_account)
        db.session.delete(connected_discord_account)

    db.session.commit()

    return jsonify(msg='Disconnected from Discord')


@api.route('users/<int:user_id>/ratings', methods=['GET'])
def get_user_ratings(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg='User not found'), 404

    return jsonify(ratings=[rating.serialize() for rating in user.ratings])


@api.route('users/<int:user_id>/ratings', methods=['POST'])
@jwt_required()
def create_user_rating(user_id):
    """Create a new rating for a user.
    Format matches the `fields` and `description` attributes of a serialized Rating object"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg=f'User not found: {user_id}'), 404

    current_user = db.session.get(User, get_jwt_identity())
    if not current_user:
        return jsonify(msg=f'User not found: {get_jwt_identity()}'), 404

    fields = request.json.get('fields', None)
    description = request.json.get('description', None)
    if not fields or not description:
        return jsonify(msg='Missing fields'), 400

    # Replace existing rating if it exists
    existing_rating = user.received_ratings.filter_by(rating_user_id=current_user.id).first()  # TODO I don't think this works
    if existing_rating:
        db.session.delete(existing_rating)

    rating = Rating(
        rating_user=current_user,
        rated_user=user,
        description=description
    )
    rating.fields.extend([RatingField(rating=rating, name=field['name'], value=field['value']) for field in fields])
    try:
        db.session.add(rating)
        db.session.commit()
    except IntegrityError:
        return jsonify(msg='Error creating rating'), 400

    return jsonify(ratings=[rating.serialize() for rating in user.ratings])


@api.route('users/<int:user_id>/ratings', methods=['DELETE'])
@jwt_required()
def delete_user_rating(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg=f'User not found: {user_id}'), 404

    current_user = db.session.get(User, get_jwt_identity())
    if not current_user:
        return jsonify(msg=f'User not found: {get_jwt_identity()}'), 404

    existing_rating = user.received_ratings.filter_by(rating_user_id=current_user.id).first()
    if existing_rating:
        db.session.delete(existing_rating)
        db.session.commit()
        return jsonify(msg='Deleted rating'), 200


@api.route('users/<int:user_id>/ratings/summary', methods=['GET'])
def get_user_ratings_summary(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(msg=f'User not found: {user_id}'), 404

    summary = {field.value: {'value': 0, 'count': 0} for field in RatingFieldName}
    for rating in user.received_ratings:
        for field in rating.fields:
            summary[field.name]['value'] += field.value
            summary[field.name]['count'] += 1

    for field in summary.keys():
        summary[field]['value'] /= summary[field]['count']

    total_rating_count = user.received_ratings.count()

    return jsonify(summary=summary, rating_count=total_rating_count)
