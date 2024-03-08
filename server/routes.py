from flask import jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity

from server import app, db
from server.models import User
from server.services import fetch_discord_account_data, validate_password


@app.route('/auth/register', methods=['POST'])
def register():
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
    return jsonify(success=True, msg='User created successfully'), 201


@app.route('/auth/login', methods=['POST'])
def login():
    # TODO actual implementation
    # For now, just check if username is "username" and password is "password"
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username is None or password is None:
        return jsonify(success=False, msg='Username or password not provided'), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify(success=False, msg='Invalid username or password'), 401

    access_token = create_access_token(identity=user.id, fresh=True)
    refresh_token = create_refresh_token(identity=user.id)
    return jsonify(success=True, access_token=access_token, refresh_token=refresh_token, msg='Logged in successfully'), 200


@app.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, fresh=False)
    return jsonify(success=True, access_token=access_token, msg='Refresh successful'), 200


@app.route('/api/hello')
def api_hello():
    return jsonify(data='Hello from the flask API')


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
