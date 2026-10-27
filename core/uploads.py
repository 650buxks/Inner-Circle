"""Checks for uploaded photos, shared by chat photos and profile photos."""

from PIL import Image

# Pillow's names for the photo types we accept. "MPO" is a JPEG with extra
# pictures inside (iPhones and many cameras save photos this way).
PHOTO_FORMATS = {"JPEG", "MPO", "PNG", "GIF", "WEBP"}


class BadUpload(Exception):
    """The upload isn't acceptable. The message is shown to the user."""


def check_photo(photo, max_size):
    """Make sure an upload is a real photo no bigger than `max_size` bytes."""
    if photo.size > max_size:
        megabytes = max_size // (1024 * 1024)
        raise BadUpload(f"Photos can be at most {megabytes} MB.")
    try:
        # Pillow reads the file itself, so a renamed .exe or a PDF called
        # "cat.jpg" is caught here, whatever its name says.
        with Image.open(photo) as image:
            image_format = image.format
            image.verify()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise BadUpload("That file isn't a photo we can show.") from None
    if image_format not in PHOTO_FORMATS:
        raise BadUpload("Photos must be JPEG, PNG, GIF or WebP.")
    photo.seek(0)  # rewind, so the whole file gets saved
