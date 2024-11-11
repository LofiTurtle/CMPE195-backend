import datetime
import os

REACT_APP_URL = os.getenv('REACT_APP_URL')
SQLALCHEMY_DATABASE_URI = "sqlite:///project.db"

DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')
DISCORD_SCOPES = ['identify']
DISCORD_AUTH_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
STEAM_CLIENT_ID = os.getenv('STEAM_CLIENT_ID')
STEAM_CLIENT_SECRET = os.getenv('STEAM_CLIENT_SECRET')
SECRET_KEY = os.getenv('SECRET_KEY')
IGDB_CLIENT_ID = os.getenv('IGDB_CLIENT_ID')
IGDB_CLIENT_SECRET = os.getenv('IGDB_CLIENT_SECRET')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_TOKEN_LOCATION = ['cookies', 'headers']
JWT_COOKIE_SECURE = False
JWT_COOKIE_CSRF_PROTECT = False
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)
UPLOAD_DIRECTORY = 'uploads'
