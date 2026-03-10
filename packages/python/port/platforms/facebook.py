"""
Facebook

This module contains an example flow of a Facebook data donation study

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
"subscription_for_no_ads.json", "other_categories_used_to_reach_you.json", "ads_feedback_activity.json", "ads_personalization_consent.json", "advertisers_you've_interacted_with.json", "advertisers_using_your_activity_or_information.json", "story_views_in_past_7_days.json", "ad_preferences.json", "groups_you've_searched_for.json", "your_search_history.json", "primary_public_location.json", "timezone.json", "primary_location.json", "your_privacy_jurisdiction.json", "people_and_friends.json", "ads_interests.json", "notifications.json", "notification_of_meta_privacy_policy_update.json", "recently_viewed.json", "recently_visited.json", "your_avatar.json", "meta_avatars_post_backgrounds.json", "contacts_sync_settings.json", "timezone.json", "autofill_information.json", "profile_information.json", "profile_update_history.json", "your_transaction_survey_information.json", "your_recently_followed_history.json", "your_recently_used_emojis.json", "no-data.txt", "navigation_bar_activity.json", "pages_and_profiles_you_follow.json", "pages_you've_liked.json", "your_saved_items.json", "fundraiser_posts_you_likely_viewed.json", "your_fundraiser_donations_information.json", "your_event_responses.json", "event_invitations.json", "your_event_invitation_links.json", "likes_and_reactions_1.json", "your_uncategorized_photos.json", "payment_history.json", "no-data.txt", "your_answers_to_membership_questions.json", "your_group_membership_activity.json", "your_contributions.json", "group_posts_and_comments.json", "your_comments_in_groups.json", "instant_games.json", "your_page_or_groups_badges.json", "instant_games_usage_data.json", "no-data.txt", "who_you've_followed.json", "people_you_may_know.json", "received_friend_requests.json", "your_friends.json",
        ],
    ),
]


def who_youve_followed_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "who_you_ve_followed.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["following_v3"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("name", "")),
                eh.epoch_to_iso(item.get("timestamp", {}))
            ))

        out = pd.DataFrame(datapoints, columns=["Name", "Timestamp"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def news_your_locations_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "facebook_news/your_locations.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["news_your_locations_v2"]  # pyright: ignore
        for item in items:
            datapoints.append(
                item
            )
        out = pd.DataFrame(datapoints, columns=["Location"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def notifications_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "notifications/notifications.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["notifications_v2"]  # pyright: ignore
        for item in items:
            denested_dict = eh.dict_denester(item)
            datapoints.append((
                eh.find_item(denested_dict, "text"),
                eh.find_item(denested_dict, "href"),
                eh.find_item(denested_dict, "unread"),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
            ))

        out = pd.DataFrame(datapoints, columns=["Text", "Link", "Gelezen", "Datum"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def content_sharing_you_have_created_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "content_sharing_links_you_have_created.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            denested_dict = eh.dict_denester(item)
            datapoints.append((
                eh.find_item(denested_dict, "href"),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
            ))

        out = pd.DataFrame(datapoints, columns=["Link", "Datum en Tijd"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def facebook_reels_usage_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "facebook_reels_usage_information.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d.get("label_values", []) #pyright: ignore
        d = items[0]
        for item in d["dict"]:
            denested_dict = eh.dict_denester(item)
            datapoints.append((
                eh.find_item(denested_dict, "label"),
                eh.find_item(denested_dict, "value"),
            ))

        out = pd.DataFrame(datapoints, columns=["Interactie met reels", "Waarde"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def last_28_days_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "your_facebook_watch_activity_in_the_last_28_days.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        denested_dict = eh.dict_denester(d)
        datapoints.append((
            eh.find_item(denested_dict, "-value"),
        ))

        out = pd.DataFrame(datapoints, columns=["Aantal"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_search_history_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "logged_information/search/your_search_history.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["searches_v2"]  # pyright: ignore
        for item in items:
            denested_dict = eh.dict_denester(item)

            datapoints.append((
                eh.fix_latin1_string(eh.find_item(denested_dict, "text")),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
            ))

        out = pd.DataFrame(datapoints, columns=["Zoekterm", "Datum"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_friends_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "your_friends.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["friends_v2"]  # pyright: ignore
        datapoints.append((len(items)))

        out = pd.DataFrame(datapoints, columns=["Aantal vrienden op facebook"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def ads_interests_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "ads_interests.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["topics_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item),
            ))
        out = pd.DataFrame(datapoints, columns=["Ad"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def recently_viewed_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "recently_viewed.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["recently_viewed"] # pyright: ignore
        for item in items:

            if "entries" in item:
                for entry in item["entries"]:
                    datapoints.append((
                        eh.fix_latin1_string(item.get("name", "")),
                        eh.fix_latin1_string(entry.get("data", {}).get("name", "")),
                        entry.get("data", {}).get("uri", ""),
                        eh.epoch_to_iso(entry.get("timestamp", ""))
                    ))

            # The nesting goes deeper
            if "children" in item:
                for child in item["children"]:
                    for entry in child["entries"]:
                        datapoints.append((
                            eh.fix_latin1_string(child.get("name", "")),
                            eh.fix_latin1_string(entry.get("data", {}).get("name", "")),
                            entry.get("data", {}).get("uri", ""),
                            eh.epoch_to_iso(entry.get("timestamp", ""))
                        ))

        out = pd.DataFrame(datapoints, columns=["Watched", "Name", "Link", "Date"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def recently_visited_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "recently_visited.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["visited_things_v2"]  # pyright: ignore
        for item in items:
            if "entries" in item:
                for entry in item["entries"]:
                    datapoints.append((
                        item.get("name", ""),
                        eh.fix_latin1_string(entry.get("data", {}).get("name", "")),
                        entry.get("data", {}).get("uri", ""),
                        eh.epoch_to_iso(entry.get("timestamp", ""))
                    ))

        out = pd.DataFrame(datapoints, columns=["Watched", "Name", "Link", "Date"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def profile_update_history_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "profile_update_history.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["profile_updates_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("title", "")),
                eh.epoch_to_iso(item.get("timestamp", ""))
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Timestamp"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)
    return out


def your_event_responses_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "your_event_responses.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["event_responses_v2"]["events_joined"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("name", "")),
                eh.epoch_to_iso(item.get("start_timestamp", ""))
            ))

        out = pd.DataFrame(datapoints, columns=["Name", "Timestamp"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def group_posts_and_comments_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "group_posts_and_comments.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        l = d["group_posts_v2"]  # pyright: ignore
        for item in l:
            denested_dict = eh.dict_denester(item)

            datapoints.append((
                eh.fix_latin1_string(eh.find_item(denested_dict, "title")),
                eh.fix_latin1_string(eh.find_item(denested_dict, "post")),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
                eh.find_item(denested_dict, "url"),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Post", "Date", "Url"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def your_answers_to_membership_questions_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "your_answers_to_membership_questions.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
                  
        items = d["group_membership_questions_answers_v2"]["group_answers"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("group_name", "")),
            ))
        out = pd.DataFrame(datapoints, columns=["Group name"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_comments_in_groups_to_df(facebook_zip: str) -> pd.DataFrame:

    b = eh.extract_file_from_zip(facebook_zip, "your_comments_in_groups.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        l = d["group_comments_v2"]  # pyright: ignore
        for item in l:
            denested_dict = eh.dict_denester(item)

            datapoints.append((
                eh.fix_latin1_string(eh.find_item(denested_dict, "title")),
                eh.fix_latin1_string(eh.find_item(denested_dict, "comment-comment")),
                eh.fix_latin1_string(eh.find_item(denested_dict, "group")),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Comment", "Group", "Timestamp"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_group_membership_activity_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "your_group_membership_activity.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["groups_joined_v2"]  # pyright: ignore
        for item in items:
            denested_dict = eh.dict_denester(item)

            datapoints.append((
                eh.fix_latin1_string(eh.find_item(denested_dict, "title")),
                eh.fix_latin1_string(eh.find_item(denested_dict, "name")),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Group name", "Timestamp"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def pages_and_profiles_you_follow_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "pages_and_profiles_you_follow.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["pages_followed_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("title", "")),
                eh.epoch_to_iso(item.get("timestamp", ""))
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Timestamp"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def pages_youve_liked_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "pages_you_ve_liked.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["page_likes_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("name", "")),
                item.get("url", ""),
                eh.epoch_to_iso(item.get("timestamp", ""))
            ))

        out = pd.DataFrame(datapoints, columns=["Name", "Url", "Timestamp"]) # pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_saved_items_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "your_saved_items.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["saves_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("title", "")),
                eh.epoch_to_iso(item.get("timestamp", ""))
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Timestamp"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out



def comments_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "comments_and_reactions/comments.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["comments_v2"]  # pyright: ignore
        for item in items:
            denested_dict = eh.dict_denester(item)

            datapoints.append((
                eh.fix_latin1_string(eh.find_item(denested_dict, "title")),
                eh.fix_latin1_string(eh.find_item(denested_dict, "comment-comment")),
                eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Comment", "Timestamp"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def likes_and_reactions_to_df(instagram_zip: str) -> pd.DataFrame:
    """
    likes_and_reactions_x
    """

    out = pd.DataFrame()
    datapoints = []
    i = 1

    while True:
        b = eh.extract_file_from_zip(instagram_zip, f"likes_and_reactions_{i}.json")
        d = eh.read_json_from_bytes(b)

        if not d:
            break

        try:
            for item in d:
                denested_dict = eh.dict_denester(item)

                datapoints.append((
                    eh.fix_latin1_string(eh.find_item(denested_dict, "title")),
                    eh.fix_latin1_string(eh.find_item(denested_dict, "reaction-reaction")),
                    eh.epoch_to_iso(eh.find_item(denested_dict, "timestamp")),
                ))

            i += 1

        except Exception as e:
            logger.error("Exception caught: %s", e)
            return pd.DataFrame()

    out = pd.DataFrame(datapoints, columns=["Title", "Reaction", "Timestamp"]) #pyright: ignore

    return out



def your_comment_active_days_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "your_comment_active_days.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["label_values"]  # pyright: ignore
        for item in items:
            datapoints.append((
                item.get("label", ""),
                item.get("value", ""),
            ))

        out = pd.DataFrame(datapoints, columns=["Label", "Value"]) #pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def likes_and_reactions_base_to_df(facebook_zip: str) -> pd.DataFrame:
    """
    Reads likes_and_reactions.json (no number suffix) or, if absent, the numbered
    variants likes_and_reactions_1.json, _2.json, … . Each item is structured with
    label_values containing Reaction, Name, and URL.
    """
    datapoints = []

    def _parse_items(d: list) -> None:
        for item in d:
            lv = {x["label"]: x.get("value", "") for x in item.get("label_values", [])}
            datapoints.append((
                lv.get("Reaction", ""),
                eh.fix_latin1_string(lv.get("Name", "")),
                lv.get("URL", ""),
                eh.epoch_to_iso(item.get("timestamp", "")),
            ))

    try:
        b = eh.extract_file_from_zip(facebook_zip, "likes_and_reactions.json")
        d = eh.read_json_from_bytes(b)
        if d:
            _parse_items(d)  # pyright: ignore
        else:
            # Fall back to numbered files for DDPs that only export _1, _2, …
            i = 1
            while True:
                b = eh.extract_file_from_zip(facebook_zip, f"likes_and_reactions_{i}.json")
                d = eh.read_json_from_bytes(b)
                if not d:
                    break
                _parse_items(d)  # pyright: ignore
                i += 1

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return pd.DataFrame(datapoints, columns=["Reaction", "Name", "URL", "Timestamp"]) if datapoints else pd.DataFrame()  # pyright: ignore


def controls_to_df(facebook_zip: str) -> pd.DataFrame:
    """
    Reads preferences/feed/controls.json.
    Top-level key "controls" is a list of groups (e.g. "Show more", "Show less"),
    each with an "entries" list.
    """
    b = eh.extract_file_from_zip(facebook_zip, "preferences/feed/controls.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        groups = d["controls"]  # pyright: ignore
        for group in groups:
            action = group.get("name", "")
            for entry in group.get("entries", []):
                denested = eh.dict_denester(entry)
                datapoints.append((
                    action,
                    eh.fix_latin1_string(eh.find_item(denested, "value")),
                    eh.epoch_to_iso(eh.find_item(denested, "timestamp")),
                ))

        out = pd.DataFrame(datapoints, columns=["Actie", "Inhoud", "Datum"])  # pyright: ignore

    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_pages_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "your_pages.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["pages_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("name", "")),
                item.get("url", ""),
                eh.epoch_to_iso(item.get("timestamp", "")),
            ))

        out = pd.DataFrame(datapoints, columns=["Name", "Url", "Timestamp"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def story_reactions_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "story_reactions.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        items = d["stories_feedback_v2"]  # pyright: ignore
        for item in items:
            datapoints.append((
                eh.fix_latin1_string(item.get("title", "")),
            ))

        out = pd.DataFrame(datapoints, columns=["Titel"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def your_posts_check_ins_to_df(facebook_zip: str) -> pd.DataFrame:
    b = eh.extract_file_from_zip(facebook_zip, "your_posts__check_ins__photos_and_videos_1.json")
    d = eh.read_json_from_bytes(b)

    out = pd.DataFrame()
    datapoints = []

    try:
        for item in d:
            datapoints.append((
                eh.fix_latin1_string(item.get("title", "")),
                eh.epoch_to_iso(item.get("timestamp", "")),
            ))

        out = pd.DataFrame(datapoints, columns=["Title", "Timestamp"]) #pyright: ignore
        
    except Exception as e:
        logger.error("Exception caught: %s", e)

    return out


def extraction(facebook_zip: str) -> list[d3i_props.PropsUIPromptConsentFormTableViz]:
    tables = [
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_who_youve_followed",
            data_frame=who_youve_followed_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Who you follow",
                "nl": "Wie je volgt",
            }),
            description=props.Translatable({
                "en": "This table shows the Facebook profiles and pages you currently follow.",
                "nl": "Deze tabel toont de Facebook-profielen en -pagina's die je momenteel volgt.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_news_your_locations",
            data_frame=news_your_locations_to_df(facebook_zip),
            title=props.Translatable({
                "en": "The locations Facebook news is set to",
                "nl": "De locaties waar Facebook Nieuws op is ingesteld",
            }),
            description=props.Translatable({
                "en": "This table displays the geographical locations for which your Facebook News feed is configured.",
                "nl": "Deze tabel toont de geografische locaties waarvoor je Facebook Nieuwsfeed is geconfigureerd.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_notifications",
            data_frame=notifications_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Notifications Facebook sent you",
                "nl": "Notificaties die Facebook je stuurde",
            }),
            description=props.Translatable({
                "en": "This table contains a history of the notifications you've received from Facebook.",
                "nl": "Deze tabel bevat een overzicht van de notificaties die je van Facebook hebt ontvangen.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_reels_usage",
            data_frame=facebook_reels_usage_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Interactions with Facebook Reels",
                "nl": "Interacties met Facebook Reels",
            }),
            description=props.Translatable({
                "en": "This table shows your interactions with Facebook Reels, such as videos you've watched or engaged with.",
                "nl": "Deze tabel toont je interacties met Facebook Reels, zoals video's die je hebt bekeken of waarmee je hebt gecommuniceerd.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_last_28",
            data_frame=last_28_days_to_df(facebook_zip),
            title=props.Translatable({
                "en": "How many videos you watched in the last 28 days",
                "nl": "Hoeveel video's je de afgelopen 28 dagen hebt bekeken",
            }),
            description=props.Translatable({
                "en": "This table indicates the number of videos you have watched on Facebook in the past 28 days.",
                "nl": "Deze tabel geeft het aantal video's aan dat je de afgelopen 28 dagen op Facebook hebt bekeken.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_search_history",
            data_frame=your_search_history_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Your search history",
                "nl": "Je zoekgeschiedenis",
            }),
            description=props.Translatable({
                "en": "This table contains a record of your search queries on Facebook.",
                "nl": "Deze tabel bevat een overzicht van je zoekopdrachten op Facebook.",
            }),
            visualizations=[
                {
                    "title": {
                        "en": "Terms you searched for",
                        "nl": "Zoektermen waar je naar zocht",
                    },
                    "type": "wordcloud",
                    "textColumn": "Zoekterm",
                    "tokenize": False,
                }
            ]
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_recently_viewed",
            data_frame=recently_viewed_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Facebook items you recently viewed",
                "nl": "Facebook items die je recentelijk hebt bekeken",
            }),
            description=props.Translatable({
                "en": "This table shows the Facebook posts, videos, and other items you have recently viewed.",
                "nl": "Deze tabel toont de Facebook-posts, video's en andere items die je recentelijk hebt bekeken.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_recently_visited",
            data_frame=recently_visited_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Profiles you visited recently",
                "nl": "Profielen die je recentelijk hebt bezocht",
            }),
            description=props.Translatable({
                "en": "This table lists the Facebook profiles you have visited most recently.",
                "nl": "Deze tabel toont de Facebook-profielen die je recentelijk hebt bezocht.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_profile_update_history",
            data_frame=profile_update_history_to_df(facebook_zip),
            title=props.Translatable({
                "en": "History of your profile updates",
                "nl": "Geschiedenis van je profielupdates",
            }),
            description=props.Translatable({
                "en": "This table contains a log of changes you've made to your Facebook profile information.",
                "nl": "Deze tabel bevat een logboek van de wijzigingen die je in je Facebook-profielinformatie hebt aangebracht.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_likes_and_reactions",
            data_frame=likes_and_reactions_base_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Likes and reactions on Facebook",
                "nl": "Likes en reacties op Facebook",
            }),
            description=props.Translatable({
                "en": "This table shows your likes and reactions to posts and other content on Facebook.",
                "nl": "Deze tabel toont je likes en reacties op berichten en andere content op Facebook.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_likes_and_reactions_titled",
            data_frame=likes_and_reactions_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Posts you liked (with title)",
                "nl": "Posts die je leuk vond (met titel)",
            }),
            description=props.Translatable({
                "en": "This table shows the titles of posts you liked on Facebook.",
                "nl": "Deze tabel toont de titels van posts die je leuk vond op Facebook.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_your_group_membership_activity",
            data_frame=your_group_membership_activity_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Facebook groups you are a member of",
                "nl": "Facebookgroepen waar je lid van bent",
            }),
            description=props.Translatable({
                "en": "This table lists the Facebook groups you are currently a member of.",
                "nl": "Deze tabel toont de Facebookgroepen waar je momenteel lid van bent.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_pages_and_profiles_you_follow",
            data_frame=pages_and_profiles_you_follow_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Pages and profiles that you follow",
                "nl": "Pagina's en profielen die je volgt",
            }),
            description=props.Translatable({
                "en": "This table displays the Facebook Pages and profiles that you actively follow.",
                "nl": "Deze tabel toont de Facebookpagina's en -profielen die je actief volgt.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_pages_youve_liked",
            data_frame=pages_youve_liked_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Pages that you have liked",
                "nl": "Pagina's die je leuk vindt",
            }),
            description=props.Translatable({
                "en": "This table contains a history of the Facebook Pages you have liked.",
                "nl": "Deze tabel bevat een overzicht van de Facebookpagina's die je leuk vindt.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_your_posts_and_check_ins",
            data_frame=your_posts_check_ins_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Your posts and check-ins",
                "nl": "Je posts en check-ins",
            }),
            description=props.Translatable({
                "en": "This table shows the posts and places you have checked into on Facebook.",
                "nl": "Deze tabel toont de berichten en plaatsen waar je op Facebook hebt ingecheckt.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_feed_controls",
            data_frame=controls_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Feed controls (show more / show less)",
                "nl": "Feed-voorkeuren (meer zien / minder zien)",
            }),
            description=props.Translatable({
                "en": "This table shows the actions you've taken to customise what content you see more or less of on Facebook.",
                "nl": "Deze tabel toont de acties die je hebt ondernomen om aan te passen welke content je meer of minder ziet op Facebook.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_content_sharing_links_you_created",
            data_frame=content_sharing_you_have_created_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Links you shared",
                "nl": "Links die je hebt gedeeld",
            }),
            description=props.Translatable({
                "en": "This table displays the external links you have shared on Facebook.",
                "nl": "Deze tabel toont de externe links die je op Facebook hebt gedeeld.",
            }),
        ),
        d3i_props.PropsUIPromptConsentFormTableViz(
            id="facebook_story_reactions",
            data_frame=story_reactions_to_df(facebook_zip),
            title=props.Translatable({
                "en": "Your story reactions",
                "nl": "Je story-reacties",
            }),
            description=props.Translatable({
                "en": "This table contains your reactions to Facebook Stories.",
                "nl": "Deze tabel bevat je reacties op Facebook Stories.",
            }),
        ),
    ]
    return [table for table in tables if not table.data_frame.empty]


class FacebookFlow(FlowBuilder):
    def __init__(self, session_id: str | int):
        super().__init__(session_id, "Facebook")
        
    def validate_file(self, file):
        return validate.validate_zip(DDP_CATEGORIES, file)
        
    def extract_data(self, file_value, validation):
        return extraction(file_value)


def process(session_id):
    flow = FacebookFlow(session_id)
    return flow.start_flow()
