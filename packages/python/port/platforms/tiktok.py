"""
TikTok

This module contains an example flow of a TikTok data donation study.

Assumptions:
It handles DDPs in the English language with filetype JSON (user_data.json).
TikTok changed their export format from .txt to .json. Several section names
also changed; both old and new names are tried when navigating the JSON.
"""

import logging

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
            "user_data_tiktok.json",
        ],
    ),
]


def _load_user_data(tiktok_zip: str) -> dict:
    """Load the TikTok export root JSON from the DDP zip."""
    for filename in ("user_data_tiktok.json", "user_data.json"):
        b = eh.extract_file_from_zip(tiktok_zip, filename)
        d = eh.read_json_from_bytes(b)
        if isinstance(d, dict) and d:
            return d
    return {}


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


def _get_first(d: dict, *paths: tuple[str | list[str], ...]):
    """Return the first non-None result across multiple candidate paths."""
    for path in paths:
        node = _get(d, *path)
        if node is not None:
            return node
    return None


def _item_get(item: dict, *keys: str):
    """Read the first present key from a record, handling case variants."""
    for key in keys:
        if key in item:
            return item.get(key)
        lower = key.lower()
        if lower in item:
            return item.get(lower)
    return ""


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

        # Each entry: (label, [preferred_key, fallback_key, ...])
        # First key found in summary wins — avoids duplicate rows when both
        # old- and new-format keys are present in the same DDP.
        metric_priority = [
            ("Videos watched since registration", ["videoCount"]),
            ("Videos watched to the end since registration", ["videosWatchedToTheEndSinceAccountRegistration"]),
            ("Videos commented on since registration", ["videosCommentedOnSinceAccountRegistration", "commentVideoCount"]),
            ("Videos shared since registration", ["videosSharedSinceAccountRegistration", "sharedVideoCount"]),
        ]
        rows = []
        for label, keys in metric_priority:
            for key in keys:
                if key in summary:
                    rows.append((label, summary[key]))
                    break
        out = pd.DataFrame(rows, columns=["Metric", "Count"])  # pyright: ignore
        out = out.rename(columns={"Metric": "Metriek", "Count": "Aantal"})
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
        settings_map = _get(
            data,
            ["App Settings", "Profile And Settings"],
            "Settings",
            "SettingsMap",
        )
        if not isinstance(settings_map, dict):
            return out

        rows = []
        content_preferences = settings_map.get("Content Preferences", {})
        if isinstance(content_preferences, dict):
            field_map = {
                "Keyword filters for videos in Following feed": "Keyword filter for videos in the following feed",
                "Keyword filters for videos in For You feed": "Keyword filters for videos in For You feed",
            }
            rows.extend(
                (label, ", ".join(content_preferences.get(key, [])))
                for key, label in field_map.items()
                if key in content_preferences
            )
        out = pd.DataFrame(rows, columns=["Setting", "Keywords"])  # pyright: ignore
        out = out.rename(columns={"Setting": "Instelling", "Keywords": "Trefwoorden"})
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
        items = _get_first(
            data,
            (["Activity", "Your Activity"], "Favorite Videos", "FavoriteVideoList"),
            ("Likes and Favorites", "Favorite Videos", "FavoriteVideoList"),
        )
        if not isinstance(items, list):
            return out
        rows = [(_item_get(item, "Date"), _item_get(item, "Link")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "Link"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "Link": "URL"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
        items = _get_first(
            data,
            (["Activity", "Your Activity"], "Follower List", "FansList"),
            ("Profile And Settings", "Follower", "FansList"),
        )
        if not isinstance(items, list):
            return out
        rows = [(_item_get(item, "Date"), _item_get(item, "UserName")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "UserName"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "UserName": "Gebruikersnaam"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
        items = _get_first(
            data,
            (["Activity", "Your Activity"], ["Following List", "Following"], "Following"),
            ("Profile And Settings", "Following", "Following"),
        )
        if not isinstance(items, list):
            return out
        rows = [(_item_get(item, "Date"), _item_get(item, "UserName")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "UserName"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "UserName": "Gebruikersnaam"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
            (_item_get(item, "HashtagName"), _item_get(item, "HashtagLink"))
            for item in items
        ]
        out = pd.DataFrame(rows, columns=["HashtagName", "HashtagLink"])  # pyright: ignore
        out = out.rename(columns={"HashtagName": "Hashtagnaam", "HashtagLink": "Hashtag-link"})
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
        items = _get_first(
            data,
            (["Activity", "Your Activity"], "Like List", "ItemFavoriteList"),
            ("Likes and Favorites", "Like List", "ItemFavoriteList"),
        )
        if not isinstance(items, list):
            return out
        rows = [(_item_get(item, "Date"), _item_get(item, "Link")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "Link"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "Link": "URL"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
        rows = [(_item_get(item, "Date"), _item_get(item, "SearchTerm")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "SearchTerm"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "SearchTerm": "Zoekterm"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
                _item_get(item, "Date"),
                _item_get(item, "SharedContent"),
                _item_get(item, "Link"),
                _item_get(item, "Method"),
            )
            for item in items
        ]
        out = pd.DataFrame(rows, columns=["Date", "SharedContent", "Link", "Method"])  # pyright: ignore
        out = out.rename(columns={
            "Date": "Datum en tijd",
            "SharedContent": "Gedeelde inhoud",
            "Link": "URL",
            "Method": "Methode",
        })
        out = out.sort_values("Datum en tijd", ascending=False)
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
        rows = [(_item_get(item, "Date"), _item_get(item, "Link")) for item in items]
        out = pd.DataFrame(rows, columns=["Date", "Link"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "Link": "URL"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
                _item_get(item, "Date"),
                _item_get(item, "Comment"),
                _item_get(item, "Photo"),
                _item_get(item, "Url"),
            )
            for item in items
        ]
        out = pd.DataFrame(rows, columns=["Date", "Comment", "Photo", "Url"])  # pyright: ignore
        out = out.rename(columns={"Date": "Datum en tijd", "Comment": "Reactie", "Photo": "Foto", "Url": "URL"})
        out = out.sort_values("Datum en tijd", ascending=False)
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
                    "textColumn": "Zoekterm",
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
                    "textColumn": "Reactie",
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
