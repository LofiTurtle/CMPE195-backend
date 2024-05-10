import requests

from server import db
from server.models import ConnectedService, ConnectedAccount


def fetch_discord_account_data(user_id: int) -> None:
    # TODO error handling like refreshing n stuff
    connected_discord_account = ConnectedAccount.query.filter_by(user_id=user_id, provider=ConnectedService.DISCORD).first()

    headers = {
        'Authorization': f'Bearer {connected_discord_account.access_token}'
    }
    user_response = requests.get('https://discord.com/api/users/@me', headers=headers)
    user_data = user_response.json()

    connected_discord_account.username = user_data['username']
    connected_discord_account.discord_user_id = user_data['id']
    connected_discord_account.profile_picture = user_data['avatar']

    db.session.add(connected_discord_account)
    db.session.commit()
