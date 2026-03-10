"""
TikTok

This module contains an example flow of a TikTok data donation study.

Assumptions:
It handles DDPs in the English language with filetype JSON (user_data.json).
TikTok changed their export format from .txt to .json. Several section names
also changed; both old and new names are tried when navigating the JSON.
"""

import logging
import io

import pandas as pd

import port.api.props as props
import port.api.d3i_props as d3i_props
import port.helpers.extraction_helpers as eh
import port.helpers.validate as validate
from port.platforms.flow_builder import FlowBuilder

from port.helpers.validate import (
    DDPCategory,
    DDPFiletype,
    Language,
)

logger = logging.getLogger(__name__)

DDP_CATEGORIES = [
    DDPCategory(
        id="json_en",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.EN,
        known_files=[
            "user_data.json",
        ],
    ),
]


def _load_user_data(tiktok_zip: str) -> dict:
    """Load user_data.json from the TikTok DDP zip."""
    b = eh.extract_file_from_zip(tiktok_zip, "user_data.json")
    d = eh.read_json_from_bytes(b)
    return d if isinstance(d, dict) else {}


def _get(d: dict, *keys: str | list[str]):
    """
    Navigate a nested dict, trying each key in order at each level.
    Accepts multiple variant names per level as a tuple or single string.
    keys is a flat list of alternating (key_or_tuple) items.
    """
    node = d
    for key in keys:
        if not isinstance(node, dict):
            return None
        if isinstance(key, (list, tuple)):
            for k in key:
                if k in node:
                    node = node[k]
                    break
            else:
                return None
        else:
            node = node.get(key)
    return node


# ---------------------------------------------------------------------------
# Extractor functions
# ---------------------------------------------------------------------------

def activity_summary_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Activity Summary > ActivitySummaryMap
    ("Activity" may now be "Your Activity")
    Columns: Metric, Count
    """
    out = pd.DataFrame()
    try:
        summary = _get(
            data,
            ["Activity", "Your Activity"],
            "Activity Summary",
            "ActivitySummaryMap",
        )
        if not isinstance(summary, dict):
            return out

        field_map = {
            "videoCount": "Videos watched since registration",
            "commentVideoCount": "Videos commented on since registration",
            "sharedVideoCount": "Videos shared since registration",
        }
        rows = [
            (label, summary.get(key, ""))
            for key, label in field_map.items()
            if key in summary
        ]
        out = pd.DataFrame(rows, columns=["Metric", "Count"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def settings_to_df(data: dict) -> pd.DataFrame:
    """
    App Settings > Settings > SettingsMap — content preference keyword filters.
    Columns: Setting, Keywords
    """
    out = pd.DataFrame()
    try:
        settings_map = _get(data, "App Settings", "Settings", "SettingsMap")
        if not isinstance(settings_map, dict):
            return out

        field_map = {
            "Following Feed Filter Keywords": "Keyword filter for videos in the following feed",
            "For You Feed Filter Keywords": "Keyword filters for videos in For You feed",
        }
        rows = [
            (label, settings_map.get(key, ""))
            for key, label in field_map.items()
            if key in settings_map
        ]
        out = pd.DataFrame(rows, columns=["Setting", "Keywords"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def favorite_videos_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Favorite Videos > FavoriteVideoList
    Columns: Date, Link
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            "Favorite Videos",
            "FavoriteVideoList",
        )
        if not isinstance(items, list):
            return out
        rows = [(item.get("Date", ""), item.get("Link", "")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "Link"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def follower_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Follower List > FansList
    Columns: Date, UserName
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            "Follower List",
            "FansList",
        )
        if not isinstance(items, list):
            return out
        rows = [(item.get("Date", ""), item.get("UserName", "")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "UserName"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def following_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Following List > Following  ("Following List" may now just be "Following")
    Columns: Date, UserName
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            ["Following List", "Following"],
            "Following",
        )
        if not isinstance(items, list):
            return out
        rows = [(item.get("Date", ""), item.get("UserName", "")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "UserName"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def hashtag_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Hashtag > HashtagList
    Columns: HashtagName, HashtagLink
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            "Hashtag",
            "HashtagList",
        )
        if not isinstance(items, list):
            return out
        rows = [
            (item.get("HashtagName", ""), item.get("HashtagLink", ""))
            for item in items
        ]
        out = pd.DataFrame(rows, columns=["HashtagName", "HashtagLink"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def like_list_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Like List > ItemFavoriteList
    Columns: Date, Link
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            "Like List",
            "ItemFavoriteList",
        )
        if not isinstance(items, list):
            return out
        rows = [(item.get("Date", ""), item.get("Link", "")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "Link"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def searches_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Search History > SearchList  ("Search History" may now be "Searches")
    Columns: Date, SearchTerm
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            ["Search History", "Searches"],
            "SearchList",
        )
        if not isinstance(items, list):
            return out
        rows = [(item.get("Date", ""), item.get("SearchTerm", "")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "SearchTerm"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def share_history_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Share History > ShareHistoryList
    Columns: Date, SharedContent, Link, Method
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            "Share History",
            "ShareHistoryList",
        )
        if not isinstance(items, list):
            return out
        rows = [
            (
                item.get("Date", ""),
                item.get("SharedContent", ""),
                item.get("Link", ""),
                item.get("Method", ""),
            )
            for item in items
        ]
        out = pd.DataFrame(rows, columns=["Date", "SharedContent", "Link", "Method"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def watch_history_to_df(data: dict) -> pd.DataFrame:
    """
    Activity > Video Browsing History > VideoList  ("Video Browsing History" may now be "Watch History")
    Columns: Date, Link
    """
    out = pd.DataFrame()
    try:
        items = _get(
            data,
            ["Activity", "Your Activity"],
            ["Video Browsing History", "Watch History"],
            "VideoList",
        )
        if not isinstance(items, list):
            return out
        rows = [(item.get("Date", ""), item.get("Link", "")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "Link"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def comments_to_df(data: dict) -> pd.DataFrame:
    """
    Comment > Comments > CommentsList
    Columns: Date, Comment, Photo, Url
    """
    out = pd.DataFrame()
    try:
        items = _get(data, "Comment", "Comments", "CommentsList")
        if not isinstance(items, list):
            return out
        rows = [
            (
                item.get("Date", ""),
                item.get("Comment", ""),
                item.get("Photo", ""),
                item.get("Url", ""),
            )
            for item in items
        ]
        out = pd.DataFrame(rows, columns=["Date", "Comment", "Photo", "Url"])  # pyright: ignore
    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extraction(tiktok_zip: str) -> list[d3i_props.PropsUIPromptConsentFormTableViz]:
    data = _load_user_data(tiktok_zip)

    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_activity_summary",
            data_frame=activity_summary_to_df(data),
            title=props.Translatable({
                "en": "Your TikTok activity summary",
                "nl": "Samenvatting van je TikTok-activiteit",
            }),
            description=props.Translatable({
                "en": "Summary counts of videos watched, commented on, and shared since account registration.",
                "nl": "Overzicht van het aantal bekeken, becommentarieerde en gedeelde video's sinds registratie.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_settings",
            data_frame=settings_to_df(data),
            title=props.Translatable({
                "en": "Content preference keyword filters",
                "nl": "Zoekwoordfilters voor contentvoorkeuren",
            }),
            description=props.Translatable({
                "en": "Keyword filters applied to your Following and For You feeds.",
                "nl": "Zoekwoordfilters die worden toegepast op je Volgend- en Voor Jou-feeds.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_watch_history",
            data_frame=watch_history_to_df(data),
            title=props.Translatable({
                "en": "Watch history",
                "nl": "Kijkgeschiedenis",
            }),
            description=props.Translatable({
                "en": "TikTok videos you have watched.",
                "nl": "TikTok-video's die je hebt bekeken.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_favorite_videos",
            data_frame=favorite_videos_to_df(data),
            title=props.Translatable({
                "en": "Favorite videos",
                "nl": "Favoriete video's",
            }),
            description=props.Translatable({
                "en": "Videos you have marked as favorites on TikTok.",
                "nl": "Video's die je als favoriet hebt gemarkeerd op TikTok.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_follower",
            data_frame=follower_to_df(data),
            title=props.Translatable({
                "en": "Your followers",
                "nl": "Je volgers",
            }),
            description=props.Translatable({
                "en": "Accounts that follow you on TikTok.",
                "nl": "Accounts die jou volgen op TikTok.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_following",
            data_frame=following_to_df(data),
            title=props.Translatable({
                "en": "Accounts you follow",
                "nl": "Accounts die je volgt",
            }),
            description=props.Translatable({
                "en": "Accounts you follow on TikTok.",
                "nl": "Accounts die je volgt op TikTok.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_hashtag",
            data_frame=hashtag_to_df(data),
            title=props.Translatable({
                "en": "Hashtags",
                "nl": "Hashtags",
            }),
            description=props.Translatable({
                "en": "Hashtags associated with your TikTok activity.",
                "nl": "Hashtags gekoppeld aan je TikTok-activiteit.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_like_list",
            data_frame=like_list_to_df(data),
            title=props.Translatable({
                "en": "Videos you liked",
                "nl": "Video's die je leuk vond",
            }),
            description=props.Translatable({
                "en": "Videos you have liked on TikTok.",
                "nl": "Video's die je leuk hebt gevonden op TikTok.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_searches",
            data_frame=searches_to_df(data),
            title=props.Translatable({
                "en": "Search history",
                "nl": "Zoekgeschiedenis",
            }),
            description=props.Translatable({
                "en": "Search terms you have used on TikTok.",
                "nl": "Zoektermen die je hebt gebruikt op TikTok.",
            }),
            visualizations=[
                {
                    "title": {"en": "Most searched terms", "nl": "Meest gezochte termen"},
                    "type": "wordcloud",
                    "textColumn": "SearchTerm",
                    "tokenize": False,
                }
            ],
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_share_history",
            data_frame=share_history_to_df(data),
            title=props.Translatable({
                "en": "Share history",
                "nl": "Deelgeschiedenis",
            }),
            description=props.Translatable({
                "en": "Content you have shared on TikTok, including when, what, and how.",
                "nl": "Inhoud die je hebt gedeeld op TikTok, inclusief wanneer, wat en hoe.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="tiktok_comments",
            data_frame=comments_to_df(data),
            title=props.Translatable({
                "en": "Your comments",
                "nl": "Je reacties",
            }),
            description=props.Translatable({
                "en": "Comments you have left on TikTok videos.",
                "nl": "Reacties die je hebt achtergelaten op TikTok-video's.",
            }),
            visualizations=[
                {
                    "title": {
                        "en": "Most common words in your comments",
                        "nl": "Meest voorkomende woorden in je reacties",
                    },
                    "type": "wordcloud",
                    "textColumn": "Comment",
                    "tokenize": True,
                }
            ],
        ),
    ]

    return [table for table in tables if not table.data_frame.empty]


class TikTokFlow(FlowBuilder):
    def __init__(self, session_id: str | int):
        super().__init__(session_id, "TikTok")

    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)

    def extract_data(self, file_value, validation):
        return extraction(file_value)


def process(session_id):
    flow = TikTokFlow(session_id)
    return flow.start_flow()
