import os
import uuid

from PIL import Image

from server import app
from server.models import User


def save_profile_picture(profile_picture) -> str:
    """Save a profile picture and return its UUID"""
    pfp_uuid = str(uuid.uuid4())
    filename = pfp_uuid + '.jpg'
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], filename))
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    pfp = Image.open(profile_picture)

    width, height = pfp.size
    size = min(width, height)
    left = (width - size) // 2
    top = (height - size) // 2
    right = left + size
    bottom = top + size
    pfp = pfp.crop((left, top, right, bottom))

    if size > 512:
        pfp = pfp.resize((512, 512))

    if pfp.mode != 'RGB':
        pfp = pfp.convert('RGB')

    pfp.save(filepath, 'JPEG')

    return pfp_uuid


def delete_profile_picture(user: User) -> None:
    """Delete a profile picture"""
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], user.profile.profile_picture_id + '.jpg'))
    if os.path.exists(filepath):
        os.remove(filepath)
