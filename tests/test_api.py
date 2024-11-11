import io

from PIL import Image

from tests.conftest import TEST_USERNAME, TEST_PASSWORD, db


def test_register(client):
    response = client.post('/api/register', json={
        'username': TEST_USERNAME,
        'password': TEST_PASSWORD
    })

    assert response.status_code == 201


def test_login(client):
    _ = client.post('/api/register', json={
        'username': TEST_USERNAME,
        'password': TEST_PASSWORD
    })

    response = client.post('/api/login', json={
        'username': TEST_USERNAME,
        'password': TEST_PASSWORD
    })

    assert response.status_code == 200


def test_logout(client, auth_headers):
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


def create_test_image(size=100):
    file = io.BytesIO()
    Image.new('RGB', (size, size), color='red').save(file, 'JPEG')
    file.seek(0)
    return file


def test_me_post(client, auth_headers):
    new_bio = 'A new bio.'
    new_pfp = create_test_image()
    response = client.post('/api/me', content_type='multipart/form-data', headers=auth_headers, data={
        'username': f'{TEST_USERNAME}_edited',
        'bio': new_bio,
        'profile_picture': (new_pfp, 'new_pfp.jpg', 'image/jpg')
    })

    assert response.status_code == 200
    assert response.json['user']['username'] == TEST_USERNAME + '_edited'
    assert response.json['user']['profile']['bio'] == new_bio
