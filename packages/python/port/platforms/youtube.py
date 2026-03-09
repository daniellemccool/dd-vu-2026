"""
YouTube

This module provides an example flow of a YouTube data donation study

Assumptions:
It handles DDPs in the Dutch and English language with filetype JSON.
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
    ValidateInput,
)

logger = logging.getLogger(__name__)

DDP_CATEGORIES = [
    DDPCategory(
        id="json_en",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.EN,
        known_files=[
            "search-history.json",
            "watch-history.json",
            "subscriptions.csv",
        ],
    ),
    DDPCategory(
        id="json_nl",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.NL,
        known_files=[
            "abonnementen.csv",
            "kijkgeschiedenis.json",
            "zoekgeschiedenis.json",
        ],
    ),
]


def watch_history_to_df(zip: str, validation) -> pd.DataFrame:

    if validation.current_ddp_category.language == Language.NL:
        b = eh.extract_file_from_zip(zip, "kijkgeschiedenis.json")
    else:
        b = eh.extract_file_from_zip(zip, "watch-history.json")

    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            datapoints.append((
                item.get("title", ""),
                item.get("titleUrl", ""),
                item.get("time", ""),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "URL", "Timestamp"])  # pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def search_history_to_df(zip: str, validation) -> pd.DataFrame:

    if validation.current_ddp_category.language == Language.NL:
        b = eh.extract_file_from_zip(zip, "zoekgeschiedenis.json")
    else:
        b = eh.extract_file_from_zip(zip, "search-history.json")

    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            datapoints.append((
                item.get("title", ""),
                item.get("titleUrl", ""),
                item.get("time", ""),
                bool(item.get("details") or []),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "URL", "Timestamp", "Ad"])  # pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def subscriptions_to_df(youtube_zip: str, validation) -> pd.DataFrame:
    """
    Parses 'subscriptions.csv' or 'abonnementen.csv' from a YouTube DDP.
    Normalises column names to English regardless of export language.
    """

    if validation.current_ddp_category.language == Language.NL:
        file_name = "abonnementen.csv"
    else:
        file_name = "subscriptions.csv"

    b = eh.extract_file_from_zip(youtube_zip, file_name)
    df = eh.read_csv_from_bytes_to_df(b)

    if not df.empty:
        df.columns = ["Channel Id", "Channel Url", "Channel Title"]  # pyright: ignore

    return df


def extraction(zip: str, validation: ValidateInput) -> list[d3i_props.PropsUIPromptConsentFormTableViz]:
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_watch_history",
            data_frame=watch_history_to_df(zip, validation),
            title=props.Translatable({
                "en": "Your watch history",
                "nl": "Je kijkgeschiedenis",
            }),
            description=props.Translatable({
                "en": "Videos you have watched on YouTube, including timestamps.",
                "nl": "Video's die je op YouTube hebt bekeken, inclusief tijdstippen.",
            }),
            visualizations=[
                {
                    "title": {
                        "en": "Words in video titles you watched",
                        "nl": "Woorden in titels van bekeken video's",
                    },
                    "type": "wordcloud",
                    "textColumn": "Title",
                    "tokenize": True,
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_search_history",
            data_frame=search_history_to_df(zip, validation),
            title=props.Translatable({
                "en": "Your search and watch history",
                "nl": "Je zoek- en kijkgeschiedenis",
            }),
            description=props.Translatable({
                "en": "Your search queries, videos watched, and ads seen on YouTube, with timestamps.",
                "nl": "Je zoekopdrachten, bekeken video's en geziene advertenties op YouTube, met tijdstippen.",
            }),
            visualizations=[
                {
                    "title": {
                        "en": "Words in your search and watch history",
                        "nl": "Woorden in je zoek- en kijkgeschiedenis",
                    },
                    "type": "wordcloud",
                    "textColumn": "Title",
                    "tokenize": True,
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="youtube_subscriptions",
            data_frame=subscriptions_to_df(zip, validation),
            title=props.Translatable({
                "en": "Your subscriptions",
                "nl": "Je abonnementen",
            }),
            description=props.Translatable({
                "en": "YouTube channels you are subscribed to.",
                "nl": "YouTube-kanalen waarop je bent geabonneerd.",
            }),
        ),
    ]

    return [table for table in tables if not table.data_frame.empty]


class YouTubeFlow(FlowBuilder):
    def __init__(self, session_id: int):
        super().__init__(session_id, "YouTube")

    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)

    def extract_data(self, file, validation):
        return extraction(file, validation)


def process(session_id):
    flow = YouTubeFlow(session_id)
    return flow.start_flow()
