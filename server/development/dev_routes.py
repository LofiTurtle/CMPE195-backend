from flask import Blueprint

from init_test_db import reset_database_schema, create_test_data, create_test_users

dev = Blueprint('dev', __name__, url_prefix='/api/dev')


@dev.route('/reset-db')
def reset_database():
    reset_database_schema()
    return {}, 204


@dev.route('/seed-users')
def seed_users():
    create_test_users()
    return {}, 204


@dev.route('/seed-data')
def seed_data():
    create_test_data()
    return {}, 204
