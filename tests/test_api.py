import os
from unittest.mock import patch

from server import routes
from server.models import User, Community, ConnectedAccount, ConnectedService
from server.services.games_service import IGDBError
from tests.conftest import TEST_USERNAME, TEST_PASSWORD, create_test_image


def test_register(client, db_session):
    """Test registering an account"""
    response = client.post('/api/register', json={
        'username': f'{TEST_USERNAME}_2',
        'password': TEST_PASSWORD
    })

    assert response.status_code == 201


def test_login(client, test_user):
    """Test logging in"""
    response = client.post('/api/login', json={
        'username': TEST_USERNAME,
        'password': TEST_PASSWORD
    })

    assert response.status_code == 200


def test_logout(client, auth_headers):
    """Test logging out"""
    response = client.post('/api/logout', headers=auth_headers)
    assert response.status_code == 200


def test_me(client, auth_headers):
    """Test getting the current user"""
    response = client.get('/api/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['user']['username'] == TEST_USERNAME


def test_me_unauthorized(client, auth_headers):
    """Test getting the current user while logged out"""
    response = client.get('/api/me')
    assert response.status_code == 401


def test_me_post(client, auth_headers):
    """Test updating user profile"""
    new_bio = 'A new bio.'
    new_pfp = create_test_image()
    response = client.put('/api/me', content_type='multipart/form-data', headers=auth_headers, data={
        'username': f'{TEST_USERNAME}_edited',
        'bio': new_bio,
        'profile_picture': (new_pfp, 'new_pfp.jpg', 'image/jpg')
    })

    assert response.status_code == 200
    assert response.json['user']['username'] == TEST_USERNAME + '_edited'
    assert response.json['user']['profile']['bio'] == new_bio


def test_get_followers(client, test_user, auth_headers, db_session):
    """Test getting the test user's followers'"""
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    test_user.followers.append(other_user)
    db_session.add(other_user)
    db_session.commit()

    response = client.get(f'/api/users/{test_user.id}/followers', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['users'][0]['username'] == other_user.username


def test_get_following(client, test_user, auth_headers, db_session):
    """Test getting the test user's following list'"""
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    other_user.followers.append(test_user)
    db_session.add(other_user)
    db_session.commit()

    response = client.get(f'/api/users/{test_user.id}/following', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['users'][0]['username'] == other_user.username


def test_follow_user(client, test_user, auth_headers, db_session):
    """Test following another user"""
    # Create another user to follow
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    db_session.commit()

    # Follow the other user
    response = client.post(f'/api/users/{other_user.id}/follow', headers=auth_headers)
    assert response.status_code == 201

    # Verify the follow relationship in the database
    test_user = User.query.get(test_user.id)  # Refresh user from db
    assert other_user in test_user.following
    assert test_user in other_user.followers


def test_follow_nonexistent_user(client, auth_headers):
    """Test following a user that doesn't exist"""
    response = client.post('/api/users/99999/follow', headers=auth_headers)
    assert response.status_code == 404
    assert response.json['msg'] == 'User not found'


def test_follow_self(client, test_user, auth_headers):
    """Test attempting to follow yourself"""
    response = client.post(f'/api/users/{test_user.id}/follow', headers=auth_headers)
    assert response.status_code == 403
    assert response.json['msg'] == 'You cannot follow yourself'


def test_follow_already_following(client, test_user, auth_headers, db_session):
    """Test following a user you're already following"""
    # Create another user and establish following relationship
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    other_user.followers.append(test_user)
    db_session.commit()

    # Try to follow again
    response = client.post(f'/api/users/{other_user.id}/follow', headers=auth_headers)
    assert response.status_code == 204


def test_unfollow_user(client, test_user, auth_headers, db_session):
    """Test unfollowing a user"""
    # Create another user and establish following relationship
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    other_user.followers.append(test_user)
    db_session.commit()

    # Unfollow the user
    response = client.delete(f'/api/users/{other_user.id}/follow', headers=auth_headers)
    assert response.status_code == 204

    # Verify the relationship is removed
    test_user = User.query.get(test_user.id)  # Refresh user from db
    assert other_user not in test_user.following
    assert test_user not in other_user.followers


def test_unfollow_nonexistent_user(client, auth_headers):
    """Test unfollowing a user that doesn't exist"""
    response = client.delete('/api/users/99999/follow', headers=auth_headers)
    assert response.status_code == 404
    assert response.json['msg'] == 'User not found'


def test_unfollow_self(client, test_user, auth_headers):
    """Test attempting to unfollow yourself"""
    response = client.delete(f'/api/users/{test_user.id}/follow', headers=auth_headers)
    assert response.status_code == 403
    assert response.json['msg'] == 'You cannot unfollow yourself'


def test_unfollow_not_following(client, test_user, auth_headers, db_session):
    """Test unfollowing a user you're not following"""
    # Create another user without following relationship
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    db_session.commit()

    # Try to unfollow
    response = client.delete(f'/api/users/{other_user.id}/follow', headers=auth_headers)
    assert response.status_code == 204


def test_get_relationship(client, test_user, auth_headers, db_session):
    """Test getting the relationship between two users"""
    # Create another user with bidirectional following
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    other_user.followers.append(test_user)  # test_user follows other_user
    other_user.following.append(test_user)  # other_user follows test_user
    db_session.commit()

    # Get relationship
    response = client.get(f'/api/users/{other_user.id}/relationship', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['following'] is True
    assert response.json['followed_by'] is True


def test_get_relationship_none(client, test_user, auth_headers, db_session):
    """Test getting relationship when there is none"""
    # Create another user with no relationship
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    db_session.commit()

    # Get relationship
    response = client.get(f'/api/users/{other_user.id}/relationship', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['following'] is False
    assert response.json['followed_by'] is False


def test_get_relationship_one_way(client, test_user, auth_headers, db_session):
    """Test getting one-way relationship"""
    # Create another user that follows test_user but isn't followed back
    other_user = User(username=f'{TEST_USERNAME}_2', password=TEST_PASSWORD)
    db_session.add(other_user)
    other_user.following.append(test_user)  # other_user follows test_user
    db_session.commit()

    # Get relationship
    response = client.get(f'/api/users/{other_user.id}/relationship', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['following'] is False
    assert response.json['followed_by'] is True


def test_get_relationship_nonexistent_user(client, auth_headers):
    """Test getting relationship with nonexistent user"""
    response = client.get('/api/users/99999/relationship', headers=auth_headers)
    assert response.status_code == 404
    assert response.json['msg'] == 'User not found'


def test_get_user_communities(client, test_user, test_community, auth_headers, db_session):
    """Test getting communities that a user follows"""
    # Add user to community
    test_user.communities.append(test_community)
    db_session.commit()

    # Get user's communities
    response = client.get(f'/api/users/{test_user.id}/communities')
    assert response.status_code == 200

    communities = response.json['communities']
    assert len(communities) == 1
    assert communities[0]['name'] == test_community.name
    assert communities[0]['id'] == test_community.id


def test_get_user_communities_empty(client, test_user, auth_headers):
    """Test getting communities for a user who doesn't follow any"""
    response = client.get(f'/api/users/{test_user.id}/communities')
    assert response.status_code == 200
    assert len(response.json['communities']) == 0


def test_get_user_communities_invalid_user(client, auth_headers):
    """Test getting communities for a non-existent user"""
    response = client.get('/api/users/999/communities')
    assert response.status_code == 404
    assert 'User not found' in response.json['msg']


def test_get_community_users(client, test_user, test_community, auth_headers, db_session):
    """Test getting users who follow a community"""
    # Add user to community
    test_community.users.append(test_user)
    db_session.commit()

    response = client.get(f'/api/communities/{test_community.id}/users')
    assert response.status_code == 200

    users = response.json['users']
    assert len(users) == 1
    assert users[0]['username'] == test_user.username
    assert users[0]['id'] == test_user.id


def test_get_community_users_empty(client, test_community, auth_headers):
    """Test getting users for a community with no followers"""
    response = client.get(f'/api/communities/{test_community.id}/users')
    assert response.status_code == 200
    assert len(response.json['users']) == 0


def test_get_community_users_invalid_community(client, auth_headers):
    """Test getting users for a non-existent community"""
    response = client.get('/api/communities/999/users')
    assert response.status_code == 404
    assert 'Community not found' in response.json['msg']


def test_follow_community(client, test_user, test_community, auth_headers):
    """Test following a community"""
    response = client.post(
        f'/api/communities/{test_community.id}/follow',
        headers=auth_headers
    )
    assert response.status_code == 201

    # Verify the relationship was created
    assert test_community in test_user.communities
    assert test_user in test_community.users


def test_follow_community_already_following(client, test_user, test_community, auth_headers, db_session):
    """Test following a community that the user already follows"""
    # Add user to community first
    test_user.communities.append(test_community)
    db_session.commit()

    response = client.post(
        f'/api/communities/{test_community.id}/follow',
        headers=auth_headers
    )
    assert response.status_code == 204


def test_follow_community_invalid_community(client, auth_headers):
    """Test following a non-existent community"""
    response = client.post('/api/communities/999/follow', headers=auth_headers)
    assert response.status_code == 404
    assert 'Community not found' in response.json['msg']


def test_unfollow_community(client, test_user, test_community, auth_headers, db_session):
    """Test unfollowing a community"""
    # Add user to community first
    test_user.communities.append(test_community)
    db_session.commit()

    response = client.delete(
        f'/api/communities/{test_community.id}/follow',
        headers=auth_headers
    )
    assert response.status_code == 204

    # Verify the relationship was removed
    assert test_community not in test_user.communities
    assert test_user not in test_community.users


def test_unfollow_community_not_following(client, test_user, test_community, auth_headers):
    """Test unfollowing a community that the user doesn't follow"""
    response = client.delete(
        f'/api/communities/{test_community.id}/follow',
        headers=auth_headers
    )
    assert response.status_code == 204


def test_unfollow_community_invalid_community(client, auth_headers):
    """Test unfollowing a non-existent community"""
    response = client.delete('/api/communities/999/follow', headers=auth_headers)
    assert response.status_code == 404
    assert 'Community not found' in response.json['msg']


def test_game_info(client, mock_igdb_game_data):
    """Test getting game info from IGDB"""

    with patch.object(routes, 'get_game') as mock_get_game:
        mock_get_game.return_value = mock_igdb_game_data
        response = client.get(f'/api/game-info/{mock_igdb_game_data["id"]}')

        assert response.status_code == 200
        assert response.json['game']['name'] == 'Test Game'
        assert response.json['game']['cover'] == '/test_cover.jpg'
        assert response.json['game']['artwork'] == '/test_artwork.jpg'
        assert response.json['game']['summary'] == 'A test game'


def test_game_info_not_found(client):
    """Test getting info for a non-existent game"""
    game_id = 999

    with patch.object(routes, 'get_game') as mock_get_game:
        mock_get_game.side_effect = IGDBError('Game not found')
        response = client.get(f'/api/game-info/{game_id}')

        assert response.status_code == 404
        assert response.json['msg'] == 'Game not found'


def test_create_community(client, auth_headers, db_session, mock_igdb_game_data):
    """Test creating a new community"""
    community_name = "Test Gaming Community"

    with patch.object(routes, 'get_game') as mock_get_game:
        mock_get_game.return_value = mock_igdb_game_data
        response = client.post('/api/communities',
                               json={
                                   'game_id': mock_igdb_game_data['id'],
                                   'community_name': community_name
                               },
                               headers=auth_headers)

        assert response.status_code == 201
        assert response.json['community']['name'] == community_name

        # Verify the community was created in the database
        community = Community.query.filter_by(name=community_name).first()
        assert community is not None
        assert community.game.name == 'Test Game'


def test_create_community_missing_name(client, auth_headers):
    """Test creating a community without a name"""
    response = client.post('/api/communities',
                           json={'game_id': 123},
                           headers=auth_headers)

    assert response.status_code == 400
    assert response.json['msg'] == 'Community name not provided'


def test_create_community_missing_game(client, auth_headers):
    """Test creating a community without a game"""
    response = client.post('/api/communities',
                           json={'community_name': 'Test Community'},
                           headers=auth_headers)

    assert response.status_code == 404
    assert response.json['msg'] == 'Game not found'


def test_create_community_unauthorized(client):
    """Test creating a community without authentication"""
    response = client.post('/api/communities',
                           json={
                               'game_id': 123,
                               'community_name': 'Test Community'
                           })

    assert response.status_code == 401


def test_get_community(client, test_community):
    """Test getting an existing community"""
    response = client.get(f'/api/communities/{test_community.id}')

    assert response.status_code == 200
    assert response.json['community']['name'] == test_community.name
    assert response.json['community']['game']['name'] == test_community.game.name


def test_get_community_not_found(client, db_session):
    """Test getting a non-existent community"""
    response = client.get('/api/communities/999')

    assert response.status_code == 404
    assert response.json['msg'] == 'Community not found'


def test_get_user_posts(client, test_user, test_post):
    """Test getting posts for a specific user"""
    response = client.get(f'/api/users/{test_user.id}/posts')
    assert response.status_code == 200
    assert len(response.json['posts']) == 1
    assert response.json['posts'][0]['title'] == "Test Post"


def test_get_user_posts_invalid_sort(client, test_user):
    """Test getting user posts with invalid sort parameter"""
    response = client.get(f'/api/users/{test_user.id}/posts?sort=invalid')
    assert response.status_code == 400
    assert 'Invalid sort type' in response.json['msg']


def test_get_user_posts_empty(client, test_user):
    """Test getting posts for a user with no posts"""
    response = client.get(f'/api/users/{test_user.id}/posts')
    assert response.status_code == 200
    assert len(response.json['posts']) == 0


def test_get_community_posts(client, test_community, test_post):
    """Test getting posts for a specific community"""
    response = client.get(f'/api/communities/{test_community.id}/posts')
    assert response.status_code == 200
    assert len(response.json['posts']) == 1
    assert response.json['posts'][0]['title'] == "Test Post"


def test_get_community_posts_invalid_sort(client, test_community):
    """Test getting community posts with invalid sort parameter"""
    response = client.get(f'/api/communities/{test_community.id}/posts?sort=invalid')
    assert response.status_code == 400
    assert 'Invalid sort type' in response.json['msg']


def test_get_community_posts_not_found(client, db_session):
    """Test getting posts for a non-existent community"""
    response = client.get('/api/communities/999/posts')
    assert response.status_code == 404
    assert 'Community not found' in response.json['msg']


def test_homepage_unauthorized(client, db_session):
    """Test getting homepage posts without authentication"""
    response = client.get('/api/homepage')
    assert response.status_code == 401


def test_homepage(client, auth_headers, test_user, test_post, test_community):
    """Test getting homepage posts for authenticated user"""
    # Add user to community to see its posts
    test_user.communities.append(test_community)
    response = client.get('/api/homepage', headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json['posts']) == 1
    assert response.json['posts'][0]['title'] == "Test Post"


def test_homepage_invalid_sort(client, auth_headers):
    """Test getting homepage with invalid sort parameter"""
    response = client.get('/api/homepage?sort=invalid', headers=auth_headers)
    assert response.status_code == 400
    assert 'Invalid sort type' in response.json['msg']


def test_get_post(client, test_post):
    """Test getting a specific post"""
    response = client.get(f'/api/posts/{test_post.id}')
    assert response.status_code == 200
    assert response.json['post']['title'] == "Test Post"
    assert response.json['post']['content'] == "Test content for the post"


def test_get_post_not_found(client, db_session):
    """Test getting a non-existent post"""
    response = client.get('/api/posts/999')
    assert response.status_code == 404
    assert 'Post not found' in response.json['msg']


def test_create_post(client, auth_headers, test_community):
    """Test creating a new post"""
    response = client.post('/api/posts',
                           headers=auth_headers,
                           data={
                               'title': 'New Test Post',
                               'content': 'New test content',
                               'community_id': test_community.id
                           }
                           )
    assert response.status_code == 201
    assert response.json['post']['title'] == 'New Test Post'
    assert response.json['post']['content'] == 'New test content'


def test_create_post_with_image(client, auth_headers, test_community):
    """Test creating a new post with an image"""
    test_image = create_test_image()
    response = client.post('/api/posts',
                           headers=auth_headers,
                           data={
                               'title': 'Post with Image',
                               'content': 'Content with image',
                               'community_id': test_community.id,
                               'image': (test_image, 'test.jpg', 'image/jpeg')
                           }
                           )
    assert response.status_code == 201
    assert response.json['post']['title'] == 'Post with Image'
    assert response.json['post']['media'] == 'image'


def test_create_post_missing_fields(client, auth_headers):
    """Test creating a post with missing required fields"""
    response = client.post('/api/posts',
                           headers=auth_headers,
                           data={
                               'title': 'Incomplete Post'
                               # Missing content and community_id
                           }
                           )
    assert response.status_code == 400
    assert 'Incomplete post' in response.json['msg']


def test_create_post_unauthorized(client, test_community):
    """Test creating a post without authentication"""
    response = client.post('/api/posts',
                           data={
                               'title': 'Unauthorized Post',
                               'content': 'Content',
                               'community_id': test_community.id
                           }
                           )
    assert response.status_code == 401


def test_get_post_image(client, test_post_with_image):
    """Test getting a post's image"""
    response = client.get(f'/api/posts/{test_post_with_image.id}/image')
    assert response.status_code == 200
    assert response.content_type == 'image/jpeg'


def test_get_post_image_no_image(client, test_post):
    """Test getting image for post without an image"""
    response = client.get(f'/api/posts/{test_post.id}/image')
    assert response.status_code == 404
    assert 'Post has no associated image' in response.json['msg']


def test_get_post_image_not_found(client, test_post_with_image, app):
    """Test getting image when file is missing"""
    # Delete the image file but keep the post record
    image_path = os.path.join(app.config['UPLOAD_DIRECTORY'], f'{test_post_with_image.image_id}.jpg')
    if os.path.exists(image_path):
        os.remove(image_path)

    response = client.get(f'/api/posts/{test_post_with_image.id}/image')
    assert response.status_code == 404
    assert 'Image for post' in response.json['msg']


def test_search_communities_by_name(client, db_session, test_game, test_community):
    """Test searching communities by community name"""
    response = client.get('/api/search/communities?q=Test')
    assert response.status_code == 200
    assert len(response.json['communities']) == 1
    assert response.json['communities'][0]['name'] == "Test Community"


def test_search_communities_by_game(client, db_session, test_game, test_community):
    """Test searching communities by game name"""
    response = client.get('/api/search/communities?q=Test Game')
    assert response.status_code == 200
    assert len(response.json['communities']) == 1
    assert response.json['communities'][0]['game']['name'] == "Test Game"


def test_search_communities_no_results(client, db_session):
    """Test searching communities with no matches"""
    response = client.get('/api/search/communities?q=NonexistentCommunity')
    assert response.status_code == 200
    assert len(response.json['communities']) == 0


def test_search_communities_no_query(client, db_session):
    """Test searching communities without a query parameter"""
    response = client.get('/api/search/communities')
    assert response.status_code == 400
    assert 'msg' in response.json


def test_search_users(client, db_session, test_user):
    """Test searching users by username"""
    response = client.get('/api/search/users?q=test')
    assert response.status_code == 200
    assert len(response.json['users']) == 1
    assert response.json['users'][0]['username'] == test_user.username


def test_search_users_no_results(client, db_session):
    """Test searching users with no matches"""
    response = client.get('/api/search/users?q=nonexistentuser')
    assert response.status_code == 200
    assert len(response.json['users']) == 0


def test_search_users_no_query(client, db_session):
    """Test searching users without a query parameter"""
    response = client.get('/api/search/users')
    assert response.status_code == 400
    assert 'msg' in response.json


def test_search_games(client, db_session, mock_igdb_search_response):
    """Test searching games through IGDB API"""
    with patch('server.routes.search_igdb_games', return_value=mock_igdb_search_response):
        response = client.get('/api/search/games?q=test')
        assert response.status_code == 200
        assert len(response.json['games']) == 1
        assert response.json['games'][0]['name'] == 'Test Game'


def test_search_games_no_query(client, db_session):
    """Test searching games without a query parameter"""
    response = client.get('/api/search/games')
    assert response.status_code == 400
    assert 'msg' in response.json


def test_search_games_api_error(client, db_session):
    """Test handling of IGDB API errors"""
    with patch('server.routes.search_igdb_games', side_effect=IGDBError('API Error')):
        response = client.get('/api/search/games?q=test')
        assert response.status_code == 404
        assert 'API Error' in response.json['msg']


def test_discord_connect(client, auth_headers, app):
    """Test the Discord connect endpoint redirects to Discord"""
    with app.test_request_context():
        response = client.get('/api/discord/connect', headers=auth_headers)

        # Should redirect to Discord's auth URL
        assert response.status_code == 302
        assert app.config['DISCORD_AUTH_URL'] in response.location
        assert app.config['DISCORD_CLIENT_ID'] in response.location
        assert app.config['DISCORD_REDIRECT_URI'] in response.location


def test_discord_connect_unauthorized(client):
    """Test Discord connect requires authentication"""
    response = client.get('/api/discord/connect')
    assert response.status_code == 401


@patch('requests.post')
def test_discord_callback_success(mock_token_request, client, auth_headers, test_user, app, db_session):
    """Test successful Discord OAuth callback"""
    # Mock Discord's token response
    mock_token_response = {
        'access_token': 'mock_access_token',
        'refresh_token': 'mock_refresh_token',
        'expires_in': 604800  # 1 week in seconds
    }
    mock_token_request.return_value.json.return_value = mock_token_response
    mock_token_request.return_value.status_code = 200

    # Mock the Discord account data fetching
    with patch.object(routes, 'fetch_discord_account_data') as mock_fetch:
        response = client.get(
            '/api/discord/callback?code=mock_code',
            headers=auth_headers
        )

        # Should redirect to user profile page
        assert response.status_code == 302
        assert f'/users/{test_user.id}' in response.location

        # Verify Discord account was created
        discord_account = ConnectedAccount.query.filter_by(
            user_id=test_user.id,
            provider=ConnectedService.DISCORD
        ).first()

        assert discord_account is not None
        assert discord_account.access_token == 'mock_access_token'
        assert discord_account.refresh_token == 'mock_refresh_token'
        assert mock_fetch.called


@patch('requests.post')
def test_discord_callback_existing_connection(
    mock_token_request, client, auth_headers, test_user, app, db_session
):
    """Test Discord callback with existing connection updates tokens"""
    # Create existing Discord connection
    existing_account = ConnectedAccount(
        user_id=test_user.id,
        username='old_username',
        provider=ConnectedService.DISCORD,
        access_token='old_token',
        refresh_token='old_refresh_token'
    )
    db_session.add(existing_account)
    db_session.commit()

    # Mock Discord's token response
    mock_token_response = {
        'access_token': 'new_access_token',
        'refresh_token': 'new_refresh_token',
        'expires_in': 604800
    }
    mock_token_request.return_value.json.return_value = mock_token_response
    mock_token_request.return_value.status_code = 200

    # Mock the Discord account data fetching
    with patch.object(routes, 'fetch_discord_account_data') as mock_fetch:
        response = client.get(
            '/api/discord/callback?code=mock_code',
            headers=auth_headers
        )

        assert response.status_code == 302

        # Verify tokens were updated
        updated_account = ConnectedAccount.query.filter_by(
            user_id=test_user.id,
            provider=ConnectedService.DISCORD
        ).first()

        assert updated_account.access_token == 'new_access_token'
        assert updated_account.refresh_token == 'new_refresh_token'
        assert mock_fetch.called


@patch('requests.post')
def test_discord_callback_invalid_code(mock_token_request, client, auth_headers):
    """Test Discord callback with invalid code"""
    # Mock Discord's error response
    mock_token_request.return_value.status_code = 400
    mock_token_request.return_value.json.return_value = {
        'error': 'invalid_grant',
        'error_description': 'Invalid authorization code'
    }

    response = client.get(
        '/api/discord/callback?code=invalid_code',
        headers=auth_headers
    )

    assert response.status_code == 400
    assert 'Invalid authorization code' in response.json['msg']


def test_discord_callback_unauthorized(client):
    """Test Discord callback requires authentication"""
    response = client.get('/api/discord/callback?code=mock_code')
    assert response.status_code == 401


def test_discord_disconnect(client, auth_headers, test_user, db_session):
    """Test disconnecting Discord account"""
    # Create Discord connection
    discord_account = ConnectedAccount(
        user_id=test_user.id,
        username='test_discord',
        provider=ConnectedService.DISCORD,
        access_token='test_token',
        refresh_token='test_refresh'
    )
    db_session.add(discord_account)
    db_session.commit()

    response = client.post('/api/discord/disconnect', headers=auth_headers)
    assert response.status_code == 200

    # Verify account was removed
    remaining_account = ConnectedAccount.query.filter_by(
        user_id=test_user.id,
        provider=ConnectedService.DISCORD
    ).first()
    assert remaining_account is None


def test_discord_disconnect_unauthorized(client):
    """Test Discord disconnect requires authentication"""
    response = client.post('/api/discord/disconnect')
    assert response.status_code == 401


def test_discord_disconnect_no_connection(client, auth_headers, test_user):
    """Test disconnecting when no Discord account is connected"""
    response = client.post('/api/discord/disconnect', headers=auth_headers)
    assert response.status_code == 200  # Should still succeed
