from datetime import datetime

from flask import jsonify, request, redirect, make_response
from flask_jwt_extended import JWTManager, decode_token, create_access_token, create_refresh_token, jwt_required, \
    get_jwt_identity, set_access_cookies, set_refresh_cookies, get_jwt, unset_access_cookies

from server import app, db, jwt
from server.models import User, Post, InvalidatedToken
from server.services import fetch_discord_account_data, validate_password
from pysteamsignin.steamsignin import SteamSignIn

@app.route('/auth/register', methods=['POST'])
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

    # TODO create UserProfile as well
    user = User(username, password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=user.id, fresh=True)
    response = jsonify(success=True, msg='User created successfully')
    set_access_cookies(response, access_token)
    return response, 201


@app.route('/auth/login', methods=['POST'])
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
    return jsonify(user.serialize())


@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify(msg='User not found'), 404
    return jsonify(data=user.serialize())


@app.route('/api/homepage', methods=['GET'])
def homepage():
    """
    :return: Posts for this user's homepage
    """
    # TODO return only posts from the user's followed communities, not all communities
    # TODO support different sorting orders
    homepage_posts = Post.query.order_by(Post.created_at.desc()).limit(10)
    return jsonify(data=[post.serialize() for post in homepage_posts])


@app.route('/api/post/<int:post_id>', methods=['GET'])
def posts(post_id):
    """
    :return: The post with the given ID
    """
    post = Post.query.filter_by(id=post_id).first()
    if not post:
        return jsonify(msg='Post not found'), 404
    return jsonify(data=post.serialize())


@app.route('/api/linked-accounts/', methods=['GET'], defaults={'user_id': None})
@app.route('/api/linked-accounts/<string:user_id>', methods=['GET'])
def get_linked_accounts(user_id):
    if user_id is None:
        # TODO use session to get current user ID
        pass

    return jsonify({
        'discord': fetch_discord_account_data(user_id),
        'steam': None
    })


@app.route('/api/linked-accounts/discord/', methods=['GET'], defaults={'user_id': None})
@app.route('/api/linked-accounts/discord/<string:user_id>', methods=['GET'])
def get_discord_account(user_id):
    # TODO set this up with real data
    print(f'would have retrieved discord info for user {user_id}')
    return jsonify(fetch_discord_account_data(user_id))

@app.route('/api/steamlogin')
def steam_login():
    received_access_token = request.headers['jwt']
    steamLogin = SteamSignIn()
    # Flask expects an explicit return on the route.
    return steamLogin.RedirectUser(steamLogin.ConstructURL('http://localhost:8080/processlogin'))


@app.route('/processlogin')
def process():

    return_data = request.values

    steamLogin = SteamSignIn()
    steam_id = steamLogin.ValidateResults(return_data)
    values = decode_token(received_access_token)
    print(values)
    print('SteamID returned is: ', steam_id)

    # if steam_id is not False:
    #     return 'We logged in successfully!<br />SteamID: {0}'.format(steam_id)
    # else:
    #     return 'Failed to log in, bad details?'

    # At this point, redirect the user to a friendly URL

    return redirect('http://localhost:5173/Dashboard')