import os
import uuid

from PIL import Image
from flask import current_app

from server.models import User


def save_image(image, max_size: int = 1024) -> str:
    pfp_uuid = str(uuid.uuid4())
    filename = pfp_uuid + '.jpg'
    filepath = os.path.abspath(os.path.join(current_app.config['UPLOAD_DIRECTORY'], filename))
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    pfp = Image.open(image)
    width, height = pfp.size

    ratio = min(max_size / width, max_size / height)
    new_width = int(width * ratio)
    new_height = int(height * ratio)

    if ratio < 1:
        pfp = pfp.resize((new_width, new_height))

    if pfp.mode != 'RGB':
        pfp = pfp.convert('RGB')

    pfp.save(filepath, 'JPEG')
    return pfp_uuid


def delete_image(image_id: str) -> None:
    """Delete a profile picture"""
    filepath = os.path.abspath(os.path.join(current_app.config['UPLOAD_DIRECTORY'], f'{image_id}.jpg'))
    if os.path.exists(filepath):
        os.remove(filepath)
