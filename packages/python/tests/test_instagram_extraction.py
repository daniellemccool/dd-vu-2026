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


def test_threads_viewed_dict_format_extracts_correctly():
    """Older dict-format threads_viewed.json (string_map_data) extracts author and date."""
    data = {
        "text_post_app_text_post_app_posts_seen": [
            {
                "string_map_data": {
                    "Author": {"value": "threaduser", "href": ""},
                    "Time": {"timestamp": 1700000000},
                    "URL": {"href": "https://threads.net/p/abc", "value": ""},
                }
            }
        ]
    }
    df = threads_viewed_to_df(make_zip({"threads_viewed.json": data}))
    assert not df.empty
    assert df["Auteur"].iloc[0] == "threaduser"
    assert "Datum en tijd" in df.columns


def test_threads_viewed_list_format_extracts_correctly():
    """Newer list-format threads_viewed.json (label_values) extracts without crash."""
    data = [
        {
            "timestamp": 1700000000,
            "label_values": [
                {"label": "Author", "value": "threaduser", "href": ""},
                {"label": "URL", "href": "https://threads.net/p/abc", "value": ""},
            ],
        }
    ]
    df = threads_viewed_to_df(make_zip({"threads_viewed.json": data}))
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert df["Auteur"].iloc[0] == "threaduser"


def test_liked_comments_dict_format_extracts_correctly():
    """Older dict-format liked_comments.json extracts account name and date."""
    data = {
        "likes_comment_likes": [
            {
                "title": "someaccount",
                "string_list_data": [
                    {"value": "Great photo!", "href": "https://www.instagram.com/p/abc/", "timestamp": 1700000000}
                ],
            }
        ]
    }
    df = liked_comments_to_df(make_zip({"liked_comments.json": data}))
    assert not df.empty
    assert df["Accountnaam"].iloc[0] == "someaccount"
    assert df["Waarde"].iloc[0] == "Great photo!"
    assert "Datum en tijd" in df.columns


def test_liked_comments_list_format_does_not_crash():
    """Newer list-format liked_comments.json returns a DataFrame without raising."""
    data = [
        {
            "timestamp": 1700000000,
            "label_values": [
                {"label": "Username", "value": "someaccount", "href": ""},
                {"label": "URL", "href": "https://www.instagram.com/p/abc/", "value": ""},
            ],
        }
    ]
    df = liked_comments_to_df(make_zip({"liked_comments.json": data}))
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Datum en tijd" in df.columns


def test_story_likes_dict_format_extracts_correctly():
    """Older dict-format story_likes.json extracts account name and date."""
    data = {
        "story_activities_story_likes": [
            {
                "title": "storyauthor",
                "string_list_data": [{"timestamp": 1700000000}],
            }
        ]
    }
    df = story_likes_to_df(make_zip({"story_likes.json": data}))
    assert not df.empty
    assert df["Account"].iloc[0] == "storyauthor"
    assert "Datum en tijd" in df.columns


def test_story_likes_list_format_does_not_crash():
    """Newer list-format story_likes.json returns a DataFrame without raising."""
    data = [
        {
            "timestamp": 1700000000,
            "label_values": [
                {"label": "Username", "value": "storyauthor", "href": ""},
            ],
        }
    ]
    df = story_likes_to_df(make_zip({"story_likes.json": data}))
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert df["Account"].iloc[0] == "storyauthor"
