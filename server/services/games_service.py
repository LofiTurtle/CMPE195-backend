import time
from datetime import datetime

import requests

from server import app
from server.models import IgdbGame


class IGDBError(Exception):
    def __init__(self, value):
        super(IGDBError, self).__init__(value)


class IGDBTokenHandler:
    def __init__(self):
        self._token = None
        self._expires = None

    def get_token(self):
        if not self._token or not self._expires or time.time() > self._expires:
            response = requests.post(f'https://id.twitch.tv/oauth2/token?'
                                     f'client_id={app.config["IGDB_CLIENT_ID"]}&'
                                     f'client_secret={app.config["IGDB_CLIENT_SECRET"]}&'
                                     f'grant_type=client_credentials')
            self._token = response.json()['access_token']
            self._expires = time.time() + response.json()['expires_in']
        return self._token

    def get_headers(self):
        return {
            'Client-ID': app.config['IGDB_CLIENT_ID'],
            'Authorization': f'Bearer {self.get_token()}',
        }


igdb_token_handler = IGDBTokenHandler()


def _update_image_urls(game, artwork=True, cover=True):
    # Increase image resolution and add protocol
    if artwork and 'artworks' in game:
        for i in range(len(game['artworks'])):
            game['artworks'][i]['url'] = 'https:' + str(game['artworks'][i]['url']).replace('/t_thumb/', '/t_1080p/', 1)

    if cover and 'cover' in game:
        game['cover']['url'] = 'https:' + str(game['cover']['url']).replace('/t_thumb/', '/t_cover_big/', 1)

    return game


def search_igdb_games(game_name):
    url = "https://api.igdb.com/v4/games"
    data = f'search "{game_name}"; fields name, cover.url, first_release_date, artworks.url, summary; limit 20;'
    response = requests.post(url, headers=igdb_token_handler.get_headers(), data=data)
    if response.status_code != 200:
        raise IGDBError(response.text)

    games = response.json()
    for i in range(len(games)):
        games[i] = _update_image_urls(games[i])

    return games


def get_game(game_id):
    url = 'https://api.igdb.com/v4/games/'
    data = f'fields name, summary, cover.url, first_release_date, artworks.url; where id = {game_id};'
    response = requests.post(url, headers=igdb_token_handler.get_headers(), data=data)
    if response.status_code != 200:
        raise IGDBError(response.text)
    game = _update_image_urls(response.json()[0])
    return game


def api_response_to_model(game):
    return IgdbGame(id=game['id'],
                    name=game['name'],
                    cover=game['cover']['url'] if 'cover' in game else None,
                    artwork=game['artworks'][0]['url'] if 'artworks' in game else None,
                    summary=game['summary'] if 'summary' in game else '',
                    first_release_date=datetime.fromtimestamp(game['first_release_date']) if 'first_release_date' in game else None,)
