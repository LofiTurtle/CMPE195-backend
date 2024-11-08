import json
import os
from datetime import datetime, timedelta
from enum import Enum
from operator import or_

import flask
import requests
from flask import jsonify, request, redirect, send_file, render_template
from flask_jwt_extended import create_access_token, jwt_required, \
    get_jwt_identity, set_access_cookies, get_jwt, unset_access_cookies

from server import app, db, jwt
from server.models import User, Post, Comment, InvalidatedToken, Community, ConnectedService, ConnectedAccount, IgdbGame
from server.services import fetch_discord_account_data, validate_password
from server.services.feed_service import get_feed_posts, SortType
from server.services.games_service import search_igdb_games, get_game, IGDBError, api_response_to_model
from server.services.media_processing import save_image, delete_image


@app.route('/api/register', methods=['POST'])
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

    access_token = create_access_token(identity=user.id, fresh=True)
    response = jsonify(success=True, msg='User created successfully')
    set_access_cookies(response, access_token)
    return response, 201


@app.route('/api/login', methods=['POST'])
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

    access_token = create_access_token(identity=user.id, fresh=True)
    response = jsonify(success=True, msg='Logged in successfully')
    set_access_cookies(response, access_token)
    return response, 200


@jwt.token_in_blocklist_loader
def is_token_revoked(jwt_headers, jwt_payload):
    """Checks if the token is revoked."""
    jti = jwt_payload['jti']
    token = db.session.query(InvalidatedToken).filter_by(token_id=jti).first()
    return token is not None


@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logs a user out, removing the access token cookie and revoking the token."""
    token = get_jwt()
    db.session.add(InvalidatedToken(token_id=token['jti'], expired_at=datetime.fromtimestamp(token['exp'])))
    db.session.commit()
    response = jsonify(msg='Logged out successfully')
    unset_access_cookies(response)
    return response, 200


@app.route('/api/me', methods=['GET'])
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


@app.route('/api/me', methods=['PATCH', 'POST'])
@jwt_required()
def edit_profile():
    """Takes username, bio, and profile_picture as form data"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify(msg='User not found'), 404

    username = request.form['username']
    bio = request.form['bio']
    profile_picture = request.files['profile_picture']

    if username:
        user.username = username
    if bio:
        user.profile.bio = bio
    if profile_picture.filename != '':
        pfp_uuid = save_image(profile_picture)
        delete_image(user.profile.profile_picture_id)
        user.profile.profile_picture_id = pfp_uuid

    db.session.add(user)
    db.session.commit()
    return jsonify(user=user.serialize())


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(user=user.serialize())


@app.route('/api/users/<int:user_id>/followers', methods=['GET'])
def get_followers(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(users=[follower.serialize() for follower in user.followers])


@app.route('/api/users/<int:user_id>/following', methods=['GET'])
def get_following(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(users=[following_user.serialize() for following_user in user.following])


@app.route('/api/users/<int:target_user_id>/follow', methods=['POST'])
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


@app.route('/api/users/<int:target_user_id>/follow', methods=['DELETE'])
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


@app.route('/api/users/<int:target_user_id>/relationship', methods=['GET'])
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


@app.route('/api/users/<int:user_id>/communities', methods=['GET'])
def get_user_communities(user_id):
    """Get the communities a user follows"""
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404

    return jsonify(communities=[community.serialize() for community in user.communities])


@app.route('/api/communities/<int:community_id>/users', methods=['GET'])
def get_community_users(community_id):
    """Get the users who follow a community"""
    community = Community.query.filter_by(id=community_id).first()
    if not community:
        return jsonify(msg='Community not found'), 404

    return jsonify(users=[user.serialize() for user in community.users])


@app.route('/api/communities/<int:community_id>/follow', methods=['POST'])
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


@app.route('/api/communities/<int:community_id>/follow', methods=['DELETE'])
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


@app.route('/api/users/<int:user_id>/profile-picture', methods=['GET'])
def get_user_profile_picture(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify(msg='User not found'), 404
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], f'{user.profile.profile_picture_id}.jpg'))
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    else:
        default_profile_filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], 'default-profile.png'))
        return send_file(default_profile_filepath, mimetype='image/png')


@app.route('/edit-profile-test', methods=['GET'])
def edit_profile_test():
    # TODO remove this after profile editing is implemented
    return render_template('edit_profile.html')


@app.route('/api/game-info/<int:game_id>', methods=['GET'])
def game_info(game_id):
    try:
        game = get_game(game_id)
        igdb_game = api_response_to_model(game)
        return jsonify(game=igdb_game.serialize())
    except IGDBError:
        return jsonify(msg='Game not found'), 404


@app.route('/api/communities', methods=['POST'])
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
    print(game)

    igdb_game = api_response_to_model(game)

    community = Community(name=community_name, game=igdb_game, owner=current_user)

    db.session.add(community)
    db.session.commit()
    return jsonify(community=community.serialize()), 201


@app.route('/api/communities/<int:community_id>', methods=['GET'])
def get_community(community_id):
    community = Community.query.get(community_id)
    if not community:
        return jsonify(msg='Community not found'), 404
    return jsonify(community=community.serialize())


def validate_sort_type(sort_type: str) -> tuple[str, bool]:
    if sort_type is None:
        # Default to 'hot' sorting
        sort_type = SortType.HOT.value
    return sort_type, sort_type in SortType


@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    sort_type, valid = validate_sort_type(request.args.get('sort'))
    if not valid:
        return jsonify(msg=f'Invalid sort type: {sort_type}'), 400
    user_posts = get_feed_posts(sort_type, user=user)
    return jsonify(posts=[post.serialize() for post in user_posts])


@app.route('/api/communities/<int:community_id>/posts', methods=['GET'])
def get_community_posts(community_id):
    community = Community.query.get(community_id)
    if not community:
        return jsonify(msg='Community not found'), 404
    sort_type, valid = validate_sort_type(request.args.get('sort'))
    if not valid:
        return jsonify(msg=f'Invalid sort type: {sort_type}'), 400
    community_posts = get_feed_posts(sort_type, community=community)
    return jsonify(posts=[post.serialize() for post in community_posts])


@app.route('/api/homepage', methods=['GET'])
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


@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """
    :return: The post with the given ID
    """
    post = Post.query.get(post_id)
    if not post:
        return jsonify(msg='Post not found'), 404
    return jsonify(post=post.serialize())


@app.route('/api/posts', methods=['POST'])
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

    app.logger.info(post)
    db.session.add(post)
    db.session.commit()

    response = jsonify(post=post.serialize())
    return response, 201


@app.route('/api/posts/<int:post_id>/image', methods=['GET'])
def get_post_image(post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify(msg='Post not found'), 404
    if post.image_id is None:
        return jsonify(msg='Post has no associated image'), 404
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], post.image_id + '.jpg'))
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    else:
        return jsonify(msg=f'Image for post with ID "{post_id}" not found'), 404


@app.route('/api/comments', methods=['POST'])
def create_comment():
    content = request.json.get('content', None)
    author_id = request.json.get('author_id', None)
    post_id = request.json.get('post_id', None)

    if content is None or author_id is None or post_id is None:
        return jsonify(success=False, msgg='Incomplete comment'), 400
    else:
        comment = Comment(
            content=content,
            author_id=author_id,
            post_id=post_id
        )
        db.session.add(comment)
        db.session.commit()

    response = jsonify(comment=comment.serialize())
    return response, 201


@app.route('/api/linked-accounts', methods=['GET'], defaults={'user_id': None})
@app.route('/api/linked-accounts/<string:user_id>', methods=['GET'])
def get_linked_accounts(user_id):
    if user_id is None:
        # TODO use session to get current user ID
        pass

    return jsonify({
        'discord': fetch_discord_account_data(user_id),
        'steam': None
    })


@app.route('/api/search/communities', methods=['GET'])
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


@app.route('/api/search/users', methods=['GET'])
def search_users():
    query = request.args.get('q')
    if not query:
        return jsonify(msg='Search query is required'), 400

    users = User.query.filter(User.username.ilike(f'%{query}%')).all()

    return jsonify(users=[user.serialize() for user in users])


@app.route('/api/search/games', methods=['GET'])
def search_games():
    search_term = request.args.get('q')
    if search_term is None:
        return jsonify(msg='No search term provided'), 400

    games = search_igdb_games(search_term)
    igdb_games = []
    for game in games:
        igdb_games.append(api_response_to_model(game))

    return jsonify(games=[game.serialize() for game in igdb_games])


@app.route('/api/discord/connect')
@jwt_required()
def discord_connect():
    params = {
        'client_id': app.config['DISCORD_CLIENT_ID'],
        'redirect_uri': app.config['DISCORD_REDIRECT_URI'],
        'response_type': 'code',
        'scope': ' '.join(app.config['DISCORD_SCOPES'])
    }
    authorization_url = app.config['DISCORD_AUTH_URL'] + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])
    return redirect(authorization_url)


@app.route('/api/discord/callback')
@jwt_required()
def discord_callback():
    code = request.args.get('code')
    data = {
        'client_id': app.config['DISCORD_CLIENT_ID'],
        'client_secret': app.config['DISCORD_CLIENT_SECRET'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': app.config['DISCORD_REDIRECT_URI']
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(app.config['DISCORD_TOKEN_URL'], data=data, headers=headers)
    token_data = response.json()

    # TODO save token to database & fetch initial info

    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    expires_in = token_data['expires_in']
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify(msg='User not found'), 401

    connected_discord_account = next((account for account in user.connected_accounts if account.provider == ConnectedService.DISCORD), None)
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
    return redirect(app.config['REACT_APP_URL'] + f'/users/{get_jwt_identity()}')


@app.route('/api/discord/disconnect', methods=['POST'])
@jwt_required()
def discord_disconnect():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify(msg='User not found'), 401

    connected_discord_account = next((account for account in user.connected_accounts if account.provider == ConnectedService.DISCORD), None)
    if connected_discord_account:
        user.connected_accounts.remove(connected_discord_account)
        db.session.delete(connected_discord_account)

    db.session.commit()

    return jsonify(msg='Disconnected from Discord')
