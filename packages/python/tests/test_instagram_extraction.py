"""
Tests for instagram.py extraction functions.

sys.modules['js'] mock must precede all port.* imports (Pyodide-only dependency).
"""
import io
import json
import sys
import zipfile
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

import pandas as pd

from port.platforms.instagram import (
    ads_viewed_to_df,
    threads_viewed_to_df,
    liked_comments_to_df,
    story_likes_to_df,
    post_comments_to_df,
)


def make_zip(files: dict) -> io.BytesIO:
    """Return an in-memory zip with each key as filename, value JSON-encoded."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, json.dumps(content))
    buf.seek(0)
    return buf
