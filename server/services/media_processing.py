import os
import uuid

from PIL import Image

from server import app
from server.models import User


def save_image(image, max_size: int = 512) -> str:
    """Save a profile picture and return its UUID"""
    pfp_uuid = str(uuid.uuid4())
    filename = pfp_uuid + '.jpg'
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], filename))
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    pfp = Image.open(image)

    width, height = pfp.size
    size = min(width, height)
    left = (width - size) // 2
    top = (height - size) // 2
    right = left + size
    bottom = top + size
    pfp = pfp.crop((left, top, right, bottom))

    if size > max_size:
        pfp = pfp.resize((max_size, max_size))

    if pfp.mode != 'RGB':
        pfp = pfp.convert('RGB')

    pfp.save(filepath, 'JPEG')

    return pfp_uuid


def delete_image(image_id: str) -> None:
    """Delete a profile picture"""
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_DIRECTORY'], f'{image_id}.jpg'))
    if os.path.exists(filepath):
        os.remove(filepath)
