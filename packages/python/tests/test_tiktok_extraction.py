"""
Baseline tests for tiktok.py extraction functions.

sys.modules['js'] mock must precede all port.* imports (Pyodide-only dependency).
"""
import io
import json
import sys
import zipfile
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

import pandas as pd

from port.platforms.tiktok import (
    _load_user_data,
    activity_summary_to_df,
    settings_to_df,
    favorite_videos_to_df,
    follower_to_df,
    following_to_df,
    hashtag_to_df,
    like_list_to_df,
    searches_to_df,
    share_history_to_df,
    watch_history_to_df,
    comments_to_df,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_zip(data: dict) -> io.BytesIO:
    """Return an in-memory zip with data serialised as user_data.json."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("user_data.json", json.dumps(data))
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# _load_user_data
# ---------------------------------------------------------------------------

def test_load_user_data_reads_user_data_json():
    """_load_user_data returns the parsed dict from user_data.json in a zip."""
    data = {"Activity": {"Follower List": {"FansList": []}}}
    result = _load_user_data(make_zip(data))
    assert result == data


def test_load_user_data_empty_zip_returns_empty_dict():
    """_load_user_data returns {} when zip contains no user_data.json."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("other_file.json", json.dumps({}))
    buf.seek(0)
    result = _load_user_data(buf)
    assert result == {}


# ---------------------------------------------------------------------------
# follower_to_df
# ---------------------------------------------------------------------------

def test_follower_to_df_activity_path():
    """follower_to_df extracts rows from Activity > Follower List > FansList."""
    data = {
        "Activity": {
            "Follower List": {
                "FansList": [
                    {"Date": "2024-01-01 10:00:00", "UserName": "alice"},
                    {"Date": "2024-01-02 11:00:00", "UserName": "bob"},
                ]
            }
        }
    }
    df = follower_to_df(data)
    assert not df.empty
    assert len(df) == 2
    assert "Datum en tijd" in df.columns
    assert "Gebruikersnaam" in df.columns
    assert df["Gebruikersnaam"].iloc[0] == "bob"


def test_follower_to_df_your_activity_path():
    """follower_to_df also handles the newer 'Your Activity' top-level key."""
    data = {
        "Your Activity": {
            "Follower List": {
                "FansList": [{"Date": "2024-01-01 10:00:00", "UserName": "newuser"}]
            }
        }
    }
    df = follower_to_df(data)
    assert not df.empty
    assert df["Gebruikersnaam"].iloc[0] == "newuser"


def test_follower_to_df_returns_empty_df_on_missing_data():
    """follower_to_df returns empty DataFrame when section is absent."""
    df = follower_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# following_to_df
# ---------------------------------------------------------------------------

def test_following_to_df_your_activity_path():
    """following_to_df handles the newer 'Your Activity' > 'Following' > 'Following' path."""
    data = {
        "Your Activity": {
            "Following": {
                "Following": [
                    {"Date": "2024-02-01 09:00:00", "UserName": "charlie"},
                ]
            }
        }
    }
    df = following_to_df(data)
    assert not df.empty
    assert "Datum en tijd" in df.columns
    assert "Gebruikersnaam" in df.columns
    assert df["Gebruikersnaam"].iloc[0] == "charlie"


def test_following_to_df_activity_following_list_path():
    """following_to_df handles the legacy 'Activity > Following List > Following' path."""
    data = {
        "Activity": {
            "Following List": {
                "Following": [{"Date": "2023-06-01 08:00:00", "UserName": "olduser"}]
            }
        }
    }
    df = following_to_df(data)
    assert not df.empty
    assert df["Gebruikersnaam"].iloc[0] == "olduser"


def test_following_to_df_returns_empty_df_on_missing_data():
    """following_to_df returns empty DataFrame when section is absent."""
    df = following_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# searches_to_df
# ---------------------------------------------------------------------------

def test_searches_to_df_extracts_search_term():
    """searches_to_df extracts Zoekterm and Datum en tijd from Activity > Search History > SearchList."""
    data = {
        "Activity": {
            "Search History": {
                "SearchList": [
                    {"Date": "2024-03-01 08:00:00", "SearchTerm": "funny cats"},
                    {"Date": "2024-03-02 08:00:00", "SearchTerm": "cooking tips"},
                ]
            }
        }
    }
    df = searches_to_df(data)
    assert not df.empty
    assert len(df) == 2
    assert "Datum en tijd" in df.columns
    assert "Zoekterm" in df.columns
    assert df["Zoekterm"].iloc[0] == "cooking tips"


def test_searches_to_df_returns_empty_df_on_missing_data():
    df = searches_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# hashtag_to_df
# ---------------------------------------------------------------------------

def test_hashtag_to_df_extracts_names_and_links():
    """hashtag_to_df extracts Hashtagnaam and Hashtag-link from Activity > Hashtag > HashtagList."""
    data = {
        "Activity": {
            "Hashtag": {
                "HashtagList": [
                    {"HashtagName": "travel", "HashtagLink": "https://tiktok.com/tag/travel"},
                    {"HashtagName": "food", "HashtagLink": "https://tiktok.com/tag/food"},
                ]
            }
        }
    }
    df = hashtag_to_df(data)
    assert not df.empty
    assert len(df) == 2
    assert "Hashtagnaam" in df.columns
    assert "Hashtag-link" in df.columns
    assert df["Hashtagnaam"].iloc[0] == "travel"
    assert df["Hashtag-link"].iloc[0] == "https://tiktok.com/tag/travel"


def test_hashtag_to_df_returns_empty_df_on_missing_data():
    df = hashtag_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# comments_to_df
# ---------------------------------------------------------------------------

def test_comments_to_df_extracts_comment_text():
    """comments_to_df extracts Reactie, Foto, URL, and Datum en tijd from Comment > Comments > CommentsList."""
    data = {
        "Comment": {
            "Comments": {
                "CommentsList": [
                    {
                        "Date": "2024-04-01 12:00:00",
                        "Comment": "Great video!",
                        "Photo": "https://photo.example.com/1",
                        "Url": "https://tiktok.com/video/1",
                    }
                ]
            }
        }
    }
    df = comments_to_df(data)
    assert not df.empty
    assert len(df) == 1
    assert "Datum en tijd" in df.columns
    assert "Reactie" in df.columns
    assert "Foto" in df.columns
    assert "URL" in df.columns
    assert df["Reactie"].iloc[0] == "Great video!"


def test_comments_to_df_returns_empty_df_on_missing_data():
    df = comments_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# watch_history_to_df
# ---------------------------------------------------------------------------

def test_watch_history_to_df_extracts_date_and_link():
    """watch_history_to_df extracts Datum en tijd and URL from Activity > Video Browsing History > VideoList."""
    data = {
        "Activity": {
            "Video Browsing History": {
                "VideoList": [
                    {"Date": "2024-05-01 10:00:00", "Link": "https://tiktok.com/video/abc"},
                ]
            }
        }
    }
    df = watch_history_to_df(data)
    assert not df.empty
    assert "Datum en tijd" in df.columns
    assert "URL" in df.columns
    assert df["URL"].iloc[0] == "https://tiktok.com/video/abc"


def test_watch_history_to_df_returns_empty_df_on_missing_data():
    df = watch_history_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# like_list_to_df
# ---------------------------------------------------------------------------

def test_like_list_to_df_extracts_date_and_link():
    """like_list_to_df extracts Datum en tijd and URL from Activity > Like List > ItemFavoriteList."""
    data = {
        "Activity": {
            "Like List": {
                "ItemFavoriteList": [
                    {"Date": "2024-05-10 14:00:00", "Link": "https://tiktok.com/video/liked1"},
                ]
            }
        }
    }
    df = like_list_to_df(data)
    assert not df.empty
    assert "Datum en tijd" in df.columns
    assert "URL" in df.columns
    assert df["URL"].iloc[0] == "https://tiktok.com/video/liked1"


def test_like_list_to_df_returns_empty_df_on_missing_data():
    df = like_list_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_like_list_to_df_likes_and_favorites_path():
    """like_list_to_df also handles 'Your Activity' path variant."""
    data = {
        "Your Activity": {
            "Like List": {
                "ItemFavoriteList": [
                    {"Date": "2024-06-01 09:00:00", "Link": "https://tiktok.com/video/fav1"},
                ]
            }
        }
    }
    df = like_list_to_df(data)
    assert not df.empty
    assert "Datum en tijd" in df.columns
    assert "URL" in df.columns


# ---------------------------------------------------------------------------
# favorite_videos_to_df
# ---------------------------------------------------------------------------

def test_favorite_videos_to_df_extracts_date_and_link():
    """favorite_videos_to_df extracts Datum en tijd and URL from Activity > Favorite Videos > FavoriteVideoList."""
    data = {
        "Activity": {
            "Favorite Videos": {
                "FavoriteVideoList": [
                    {"Date": "2024-06-15 16:00:00", "Link": "https://tiktok.com/video/fav"},
                ]
            }
        }
    }
    df = favorite_videos_to_df(data)
    assert not df.empty
    assert "Datum en tijd" in df.columns
    assert "URL" in df.columns
    assert df["URL"].iloc[0] == "https://tiktok.com/video/fav"


def test_favorite_videos_to_df_returns_empty_df_on_missing_data():
    df = favorite_videos_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# share_history_to_df
# ---------------------------------------------------------------------------

def test_share_history_to_df_extracts_all_fields():
    """share_history_to_df extracts Datum en tijd, Gedeelde inhoud, URL, Methode from ShareHistoryList."""
    data = {
        "Activity": {
            "Share History": {
                "ShareHistoryList": [
                    {
                        "Date": "2024-07-01 11:00:00",
                        "SharedContent": "Funny clip",
                        "Link": "https://tiktok.com/video/shared1",
                        "Method": "WhatsApp",
                    }
                ]
            }
        }
    }
    df = share_history_to_df(data)
    assert not df.empty
    assert "Datum en tijd" in df.columns
    assert "Gedeelde inhoud" in df.columns
    assert "URL" in df.columns
    assert "Methode" in df.columns
    assert df["Methode"].iloc[0] == "WhatsApp"
    assert df["Gedeelde inhoud"].iloc[0] == "Funny clip"


def test_share_history_to_df_returns_empty_df_on_missing_data():
    df = share_history_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# activity_summary_to_df
# ---------------------------------------------------------------------------

def test_activity_summary_to_df_activity_key():
    """activity_summary_to_df extracts rows via the older 'Activity' top-level key."""
    data = {
        "Activity": {
            "Activity Summary": {
                "ActivitySummaryMap": {
                    "videoCount": "1500",
                    "commentVideoCount": "42",
                    "sharedVideoCount": "10",
                }
            }
        }
    }
    df = activity_summary_to_df(data)
    assert not df.empty
    assert "Metriek" in df.columns
    assert "Aantal" in df.columns
    assert len(df) == 3


def test_activity_summary_to_df_your_activity_key():
    """activity_summary_to_df also handles the newer 'Your Activity' top-level key."""
    data = {
        "Your Activity": {
            "Activity Summary": {
                "ActivitySummaryMap": {
                    "videoCount": "800",
                    "sharedVideoCount": "5",
                }
            }
        }
    }
    df = activity_summary_to_df(data)
    assert not df.empty
    assert "Metriek" in df.columns
    assert "Aantal" in df.columns
    assert len(df) == 2


def test_activity_summary_to_df_returns_empty_df_on_missing_data():
    df = activity_summary_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ---------------------------------------------------------------------------
# settings_to_df
# ---------------------------------------------------------------------------

def test_settings_to_df_extracts_keyword_filters():
    """settings_to_df extracts Instelling and Trefwoorden from App Settings > Settings > SettingsMap > Content Preferences."""
    data = {
        "App Settings": {
            "Settings": {
                "SettingsMap": {
                    "Content Preferences": {
                        "Keyword filters for videos in Following feed": ["spam", "ads"],
                        "Keyword filters for videos in For You feed": ["violence"],
                    }
                }
            }
        }
    }
    df = settings_to_df(data)
    assert not df.empty
    assert "Instelling" in df.columns
    assert "Trefwoorden" in df.columns
    assert len(df) == 2


def test_settings_to_df_returns_empty_df_on_missing_data():
    df = settings_to_df({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_activity_summary_no_duplicate_rows_when_old_and_new_keys_present():
    """When a DDP contains both old and new key names for the same metric,
    only one row per metric should appear."""
    data = {
        "Activity": {
            "Activity Summary": {
                "ActivitySummaryMap": {
                    "commentVideoCount": 10,
                    "sharedVideoCount": 5,
                    "videosCommentedOnSinceAccountRegistration": 10,
                    "videosSharedSinceAccountRegistration": 5,
                }
            }
        }
    }
    df = activity_summary_to_df(data)
    assert df["Metriek"].duplicated().sum() == 0
    assert len(df) == 2


def test_searches_to_df_sorted_newest_first():
    """Results are sorted by date descending (newest entry first)."""
    data = {
        "Activity": {
            "Search History": {
                "SearchList": [
                    {"Date": "2023-01-01 00:00:00", "SearchTerm": "older"},
                    {"Date": "2024-06-01 00:00:00", "SearchTerm": "newer"},
                ]
            }
        }
    }
    df = searches_to_df(data)
    assert "Datum en tijd" in df.columns
    assert df["Datum en tijd"].iloc[0] == "2024-06-01 00:00:00"
    assert df["Datum en tijd"].iloc[1] == "2023-01-01 00:00:00"


def test_watch_history_to_df_has_datum_en_tijd_column():
    data = {
        "Activity": {
            "Video Browsing History": {
                "VideoList": [{"Date": "2023-12-01 10:00:00", "Link": "https://tiktok.com/v/abc"}]
            }
        }
    }
    df = watch_history_to_df(data)
    assert "Datum en tijd" in df.columns
    assert "Datum" not in df.columns
