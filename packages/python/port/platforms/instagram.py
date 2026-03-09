"""
Instagram

This module contains an example flow of a Instagram data donation study

Assumptions:
It handles DDPs in the english language with filetype JSON.
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
            "secret_conversations.json",
            "personal_information.json",
            "account_privacy_changes.json",
            "account_based_in.json",
            "recently_deleted_content.json",
            "liked_posts.json",
            "stories.json",
            "profile_photos.json",
            "followers.json",
            "signup_information.json",
            "comments_allowed_from.json",
            "login_activity.json",
            "your_topics.json",
            "camera_information.json",
            "recent_follow_requests.json",
            "devices.json",
            "professional_information.json",
            "follow_requests_you've_received.json",
            "eligibility.json",
            "pending_follow_requests.json",
            "videos_watched.json",
            "ads_interests.json",
            "account_searches.json",
            "profile_searches.json",
            "followers_1.json",
            "saved_posts.json",
            "following.json",
            "posts_viewed.json",
            "recently_unfollowed_accounts.json",
            "post_comments.json",
            "account_information.json",
            "accounts_you're_not_interested_in.json",
            "use_cross-app_messaging.json",
            "profile_changes.json",
            "reels.json",
        ],
    )
]



def followers_to_df(instagram_zip: str) -> pd.DataFrame:
    """
    followers_1.json can be a bare top-level list (newer exports) or wrapped
    under a 'relationships_followers' key (older exports).
    """

    b = eh.extract_file_from_zip(instagram_zip, "followers_1.json")
    data = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        # Newer format: top-level list; older format: dict with relationships_followers key
        if isinstance(data, dict):
            items = data.get("relationships_followers", [])
        else:
            items = data  # pyright: ignore

        for item in items:
            d = eh.dict_denester(item)
            datapoints.append((
                eh.fix_latin1_string(eh.find_item(d, "value")),
                eh.find_item(d, "href"),
                eh.epoch_to_iso(eh.find_item(d, "timestamp"))
            ))
        out = pd.DataFrame(datapoints, columns=["Account", "Link", "Date"]) # pyright: ignore
        out = out.sort_values(by="Date", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Date": "Datum"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def profile_searches_to_df(instagram_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(instagram_zip, "profile_searches.json")
    data = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = data["searches_user"]  # pyright: ignore
        for item in items:
            d = eh.dict_denester(item)
            datapoints.append((
                eh.epoch_to_iso(eh.find_item(d, "timestamp")),
                eh.fix_latin1_string(eh.find_item(d, "value")),
            ))
        out = pd.DataFrame(datapoints, columns=["Timestamp", "Name"]) # pyright: ignore
        out = out.sort_values(by="Timestamp", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Timestamp": "Datum en tijd", "Name": "Naam"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def saved_posts_to_df(instagram_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(instagram_zip, "saved_posts.json")
    data = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = data["saved_saved_media"]  # pyright: ignore
        for item in items:
            title = eh.fix_latin1_string(item.get("title", ""))
            string_list = item.get("string_list_data", [{}])
            entry = string_list[0] if string_list else {}
            datapoints.append((
                title,
                entry.get("href", ""),
                eh.epoch_to_iso(entry.get("timestamp", "")),
            ))
        out = pd.DataFrame(datapoints, columns=["Title", "Href", "Timestamp"]) # pyright: ignore
        out = out.sort_values(by="Timestamp", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Title": "Titel", "Href": "URL", "Timestamp": "Datum en tijd"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def posts_viewed_to_df(instagram_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(instagram_zip, "posts_viewed.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["impressions_history_posts_seen"] # pyright: ignore
        for item in items:
            data = item.get("string_map_data", {})
            account_name = data.get("Author", {}).get("value", None)
            if "Time" in data:
                timestamp = data.get("Time", {}).get("timestamp", "")
            else:
                timestamp = data.get("Tijd", {}).get("timestamp", "")

            datapoints.append((
                account_name,
                eh.epoch_to_iso(timestamp)
            ))
        out = pd.DataFrame(datapoints, columns=["Author", "Date"]) # pyright: ignore
        out = out.sort_values(by="Date", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Author": "Auteur", "Date": "Datum"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def videos_watched_to_df(instagram_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(instagram_zip, "videos_watched.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["impressions_history_videos_watched"] # pyright: ignore
        for item in items:
            data = item.get("string_map_data", {})
            account_name = data.get("Author", {}).get("value", None)
            if "Time" in data:
                timestamp = data.get("Time", {}).get("timestamp", "")
            else:
                timestamp = data.get("Tijd", {}).get("timestamp", "")

            datapoints.append((
                account_name,
                eh.epoch_to_iso(timestamp)
            ))
        out = pd.DataFrame(datapoints, columns=["Author", "Date"]) # pyright: ignore
        out = out.sort_values(by="Date", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Author": "Auteur", "Date": "Datum"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def following_to_df(instagram_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(instagram_zip, "following.json")
    data = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = data["relationships_following"] # pyright: ignore
        for item in items:
            d = eh.dict_denester(item)
            datapoints.append((
                eh.fix_latin1_string(eh.find_item(d, "value")),
                eh.find_item(d, "href"),
                eh.epoch_to_iso(eh.find_item(d, "timestamp"))
            ))
        out = pd.DataFrame(datapoints, columns=["Account", "Link", "Date"]) # pyright: ignore
        out = out.sort_values(by="Date", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Date": "Datum"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def liked_posts_to_df(instagram_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(instagram_zip, "liked_posts.json")
    data = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = data["likes_media_likes"] #pyright: ignore
        for item in items:
            d = eh.dict_denester(item)
            datapoints.append((
                eh.fix_latin1_string(eh.find_item(d, "title")),
                eh.fix_latin1_string(eh.find_item(d, "value")),
                eh.find_items(d, "href"),
                eh.epoch_to_iso(eh.find_item(d, "timestamp"))
            ))
        out = pd.DataFrame(datapoints, columns=["Account name", "Value", "Link", "Date"]) # pyright: ignore
        out = out.sort_values(by="Date", key=eh.sort_isotimestamp_empty_timestamp_last)
        out = out.rename(columns={"Account name": "Accountnaam", "Value": "Waarde", "Date": "Datum"})

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def extraction(instagram_zip: str) -> list[d3i_props.PropsUIPromptConsentFormTableViz]:
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_followers",
            data_frame=followers_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Your Instagram followers",
                "nl": "Je Instagram-volgers"
            }),
            description=props.Translatable({
                "en": "List of accounts that follow you on Instagram.",
                "nl": "Lijst van accounts die jou op Instagram volgen."
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_following",
            data_frame=following_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Accounts that you follow on Instagram",
                "nl": "Accounts die je volgt op Instagram"
            }),
            description=props.Translatable({
                "en": "In this table, you find the accounts that you follow on Instagram.",
                "nl": "In deze tabel zie je de accounts die je volgt op Instagram."
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_posts_viewed",
            data_frame=posts_viewed_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Posts viewed on Instagram",
                "nl": "Berichten bekeken op Instagram"
            }),
            description=props.Translatable({
                "en": "In this table you find the accounts of posts you viewed on Instagram sorted over time. Below, you find visualizations of different parts of this table. First, you find a timeline showing you the number of posts you viewed over time. Next, you find a histogram indicating how many posts you have viewed per hour of the day.",
                "nl": "In deze tabel zie je de accounts van berichten die je op Instagram hebt bekeken, gesorteerd op tijd. Hieronder vind je visualisaties van verschillende onderdelen van deze tabel. Eerst zie je een tijdlijn met het aantal berichten dat je in de loop van de tijd hebt bekeken. Daarna zie je een histogram dat aangeeft hoeveel berichten je per uur van de dag hebt bekeken."
            }),
            visualizations=[
                {
                    "title": {
                        "en": "The total number of Instagram posts you viewed over time",
                        "nl": "Het totale aantal Instagram-berichten dat je in de loop van de tijd hebt bekeken"
                    },
                    "type": "area",
                    "group": {
                        "column": "Datum",
                        "dateFormat": "auto",
                    },
                    "values": [{
                        "label": "Count",
                        "aggregate": "count",
                    }]
                },
                {
                    "title": {
                        "en": "The total number of Instagram posts you have viewed per hour of the day",
                        "nl": "Het totale aantal Instagram-berichten dat je per uur van de dag hebt bekeken"
                    },
                    "type": "bar",
                    "group": {
                        "column": "Datum",
                        "dateFormat": "hour_cycle",
                        "label": "Hour of the day",
                    },
                    "values": [{
                        "label": "Count"
                    }]
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_videos_watched",
            data_frame=videos_watched_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Videos watched on Instagram",
                "nl": "Video's bekeken op Instagram"
            }),
            description=props.Translatable({
                "en": "In this table you find the accounts of videos you watched on Instagram sorted over time. Below, you find a timeline showing you the number of videos you watched over time.",
                "nl": "In deze tabel zie je de accounts van video's die je op Instagram hebt bekeken, gesorteerd op tijd. Hieronder zie je een tijdlijn met het aantal video's dat je in de loop van de tijd hebt bekeken."
            }),
            visualizations=[
                {
                    "title": {
                        "en": "The total number of videos watched on Instagram over time",
                        "nl": "Het totale aantal video's dat je op Instagram hebt bekeken in de loop van de tijd"
                    },
                    "type": "area",
                    "group": {
                        "column": "Datum",
                        "dateFormat": "auto"
                    },
                    "values": [{
                        "aggregate": "count",
                        "label": "Count"
                    }]
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_liked_posts",
            data_frame=liked_posts_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Instagram liked posts",
                "nl": "Instagram-berichten die je leuk vond"
            }),
            description=props.Translatable({
                "en": "",
                "nl": ""
            }),
            visualizations=[
                {
                    "title": {
                        "en": "Most liked accounts",
                        "nl": "Meest gelikete accounts"
                    },
                    "type": "wordcloud",
                    "textColumn": "Accountnaam",
                    "tokenize": False,
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_profile_searches",
            data_frame=profile_searches_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Your Instagram profile searches",
                "nl": "Je Instagram-profielzoekopdrachten"
            }),
            description=props.Translatable({
                "en": "List of profiles you have searched for on Instagram.",
                "nl": "Lijst van profielen die je op Instagram hebt gezocht."
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="instagram_saved_posts",
            data_frame=saved_posts_to_df(instagram_zip),
            title=props.Translatable({
                "en": "Your saved posts on Instagram",
                "nl": "Je opgeslagen berichten op Instagram"
            }),
            description=props.Translatable({
                "en": "List of posts you have saved on Instagram.",
                "nl": "Lijst van berichten die je hebt opgeslagen op Instagram."
            }),
        ),
    ]

    return [table for table in tables if not table.data_frame.empty]


class InstagramFlow(FlowBuilder):
    def __init__(self, session_id: int):
        super().__init__(session_id, "Instagram")
        
    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)
        
    def extract_data(self, file_value, validation):
        return extraction(file_value)


def process(session_id):
    flow = InstagramFlow(session_id)
    return flow.start_flow()
