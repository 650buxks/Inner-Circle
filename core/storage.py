"""Saves uploaded files (chat photos) to Cloudinary.

Django saves files through a "storage" class. The default one writes to the
server's disk, but Render's free disk is wiped on every deploy, so in
production we use this one instead (see STORAGES in settings.py). The rest
of the code doesn't know or care where files end up.

Cloudinary reads its login details from the CLOUDINARY_URL environment
variable by itself.
"""

from pathlib import PurePosixPath

import cloudinary
import cloudinary.uploader
from django.core.files.storage import Storage


def _public_id(name):
    """Cloudinary's name for a file: the path without the extension."""
    return str(PurePosixPath(name).with_suffix(""))


class CloudinaryStorage(Storage):
    def _save(self, name, content):
        result = cloudinary.uploader.upload(
            content,
            public_id=_public_id(name),
            resource_type="image",
        )
        return f"{result['public_id']}.{result['format']}"

    def url(self, name):
        # f_auto and q_auto: Cloudinary picks the smallest format and
        # quality that still looks good on each device.
        return cloudinary.CloudinaryImage(_public_id(name)).build_url(
            secure=True,
            fetch_format="auto",
            quality="auto",
        )

    def delete(self, name):
        cloudinary.uploader.destroy(_public_id(name), resource_type="image")

    def exists(self, name):
        # File names include a random part, so they never clash.
        return False
