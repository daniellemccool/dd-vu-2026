"""
Chrome

This module contains an example flow of a Chrome browser history data donation study.

Assumptions:
It handles DDPs in the english and dutch language with filetype JSON.
"""
from html.parser import HTMLParser
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
            "Autofill.json",
            "Bookmarks.html",
            "BrowserHistory.json",
            "Device Information.json",
            "Dictionary.csv",
            "Extensions.json",
            "Omnibox.json",
            "OS Settings.json",
            "ReadingList.html",
            "SearchEngines.json",
            "SyncSettings.json",
        ],
    ),
    DDPCategory(
        id="json_nl",
        ddp_filetype=DDPFiletype.JSON,
        language=Language.NL,
        known_files=[
            "Adressen en meer.json",
            "Bookmarks.html",
            "Geschiedenis.json",
            "Leeslijst.html",
            "Woordenboek.csv",
            "Apparaatgegevens.json",
            "Extensies.json",
            "Instellingen.json",
            "OS-instellingen.json",
        ],
    ),
]


class _BookmarkParser(HTMLParser):
    """Minimal HTML parser to extract <a> tags from bookmarks HTML."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get("href", "")
            self._current_text = ""

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text = data

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href is not None:
            self.links.append((self._current_text, self._current_href))
            self._current_href = None


def browser_history_to_df(chrome_zip) -> pd.DataFrame:
    """
    Extract browser history from BrowserHistory.json or Geschiedenis.json (NL).
    """
    b = eh.extract_file_from_zip(chrome_zip, "Geschiedenis.json")
    d = eh.read_json_from_bytes(b)

    if not d:
        b = eh.extract_file_from_zip(chrome_zip, "BrowserHistory.json")
        d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["Browser History"]  # type: ignore
        for item in items:
            datapoints.append((
                item.get("title", None),
                item.get("url", None),
                item.get("page_transition", None),
                eh.epoch_to_iso(item.get("time_usec", 0) / 1_000_000),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Url", "Transition", "Date"])
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def bookmarks_to_df(chrome_zip) -> pd.DataFrame:
    """
    Extract bookmarks from Bookmarks.html.
    """
    b = eh.extract_file_from_zip(chrome_zip, "Bookmarks.html")
    out = pd.DataFrame()

    try:
        html_content = b.read().decode("utf-8", errors="replace")
        parser = _BookmarkParser()
        parser.feed(html_content)
        out = pd.DataFrame(parser.links, columns=["Bookmark", "Url"])
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def omnibox_to_df(chrome_zip) -> pd.DataFrame:
    """
    Extract omnibox (address bar) history from Omnibox.json.
    """
    b = eh.extract_file_from_zip(chrome_zip, "Omnibox.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["Typed Url"]  # type: ignore
        for item in items:
            datapoints.append((
                item.get("title", None),
                len(item.get("visits", [])),
                item.get("url", None),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Number of visits", "Url"])
        out = out.sort_values(by="Number of visits", ascending=False).reset_index(drop=True)
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def extraction(chrome_zip) -> list:
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="chrome_browser_history",
            data_frame=browser_history_to_df(chrome_zip),
            title=props.Translatable({
                "en": "Chrome browser history",
                "nl": "Chrome browsergeschiedenis",
            }),
            description=props.Translatable({
                "en": "The websites you have visited using Chrome",
                "nl": "De websites die u heeft bezocht met Chrome",
            }),
            visualizations=[
                {
                    "title": {"en": "Most visited websites", "nl": "Meest bezochte websites"},
                    "type": "wordcloud",
                    "textColumn": "Url",
                    "tokenize": False,
                }
            ],
            data_frame_max_size=10000,
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="chrome_bookmarks",
            data_frame=bookmarks_to_df(chrome_zip),
            title=props.Translatable({
                "en": "Chrome bookmarks",
                "nl": "Chrome bladwijzers",
            }),
            description=props.Translatable({
                "en": "Websites you have bookmarked in Chrome",
                "nl": "Websites die u heeft opgeslagen als bladwijzer in Chrome",
            }),
            data_frame_max_size=10000,
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="chrome_omnibox",
            data_frame=omnibox_to_df(chrome_zip),
            title=props.Translatable({
                "en": "Chrome address bar history",
                "nl": "Chrome adresbalk geschiedenis",
            }),
            description=props.Translatable({
                "en": "URLs you have typed directly into the Chrome address bar",
                "nl": "URLs die u direct in de Chrome adresbalk heeft ingevoerd",
            }),
            data_frame_max_size=10000,
        ),
    ]

    return [table for table in tables if not table.data_frame.empty]


class ChromeFlow(FlowBuilder):
    def __init__(self, session_id: int):
        super().__init__(session_id, "Chrome")

    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)

    def extract_data(self, file_value, validation):
        return extraction(file_value)


def process(session_id):
    flow = ChromeFlow(session_id)
    return flow.start_flow()
