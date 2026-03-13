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


def test_ads_viewed_list_format_extracts_correctly():
    """Newer list-format ads_viewed.json extracts account and date."""
    data = [
        {
            "timestamp": 1700000000,
            "label_values": [
                {"label": "Username", "value": "testaccount", "href": ""},
                {"label": "Name", "value": "Test Ad Account", "href": ""},
                {"label": "URL", "href": "https://example.com", "value": ""},
            ],
        }
    ]
    df = ads_viewed_to_df(make_zip({"ads_viewed.json": data}))
    assert not df.empty
    assert len(df) == 1
    assert "Datum en tijd" in df.columns
    assert df["Account"].iloc[0] == "testaccount"


def test_ads_viewed_dict_format_does_not_crash():
    """Older dict-format ads_viewed.json returns a DataFrame without raising."""
    data = {
        "impressions_history_ads_seen": [
            {
                "timestamp": 1700000000,
                "label_values": [
                    {"label": "Username", "value": "testaccount", "href": ""},
                ],
            }
        ]
    }
    df = ads_viewed_to_df(make_zip({"ads_viewed.json": data}))
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) == 1
    assert df["Account"].iloc[0] == "testaccount"


def test_ads_viewed_unknown_format_returns_empty():
    """Completely unexpected format (e.g. empty dict) returns empty DataFrame."""
    df = ads_viewed_to_df(make_zip({"ads_viewed.json": {}}))
    assert isinstance(df, pd.DataFrame)
    assert df.empty
