# --------------------------------------------------------------------
# Multi-platform data donation script for the VU 2026 study.
#
# Participants are prompted for data from each platform in sequence.
# For each platform:
#   1. They are asked to submit their DDP zip file
#   2. The file is validated for that platform
#   3. Extracted data is shown for review and consent
#   4. Donated data is sent per platform
#
# Platforms: LinkedIn, Instagram, Chrome, Facebook, YouTube, TikTok, X (Twitter)
# --------------------------------------------------------------------

import json
import logging

import port.api.props as props
import port.helpers.port_helpers as ph

import port.platforms.linkedin as linkedin
import port.platforms.instagram as instagram
import port.platforms.chrome as chrome
import port.platforms.facebook as facebook
import port.platforms.youtube as youtube
import port.platforms.tiktok as tiktok
import port.platforms.x as x

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)

logger = logging.getLogger("script")


def process(session_id: str):
    logger.info("Starting the donation flow for session %s", session_id)

    platforms = [
        ("LinkedIn",  linkedin.LinkedInFlow(session_id)),
        ("Instagram", instagram.InstagramFlow(session_id)),
        ("Chrome",    chrome.ChromeFlow(session_id)),
        ("Facebook",  facebook.FacebookFlow(session_id)),
        ("YouTube",   youtube.YouTubeFlow(session_id)),
        ("TikTok",    tiktok.TikTokFlow(session_id)),
        ("X",         x.XFlow(session_id)),
    ]

    for platform_name, flow in platforms:
        logger.info("Starting platform: %s", platform_name)
        table_list = None

        # File submission loop — keep prompting until valid file or skip
        while True:
            file_prompt = ph.generate_file_prompt("application/zip, text/plain")
            file_result = yield ph.render_page(
                flow.UI_TEXT["submit_file_header"], file_prompt
            )

            if file_result.__type__ == "PayloadFile":
                validation = flow.validate_file(file_result.value)

                if validation.get_status_code_id() == 0:
                    logger.info("Valid %s file received", platform_name)
                    table_list = flow.extract_data(file_result.value, validation)
                    break

                else:
                    logger.info("Invalid %s file; prompting retry", platform_name)
                    retry_prompt = ph.generate_retry_prompt(platform_name)
                    retry_result = yield ph.render_page(
                        flow.UI_TEXT["retry_header"], retry_prompt
                    )
                    if retry_result.__type__ == "PayloadTrue":
                        continue
                    else:
                        break

            else:
                logger.info("Skipped %s", platform_name)
                break

        # Consent and donation
        if table_list is not None:
            logger.info("Showing consent for %s", platform_name)
            review_prompt = ph.generate_review_data_prompt(
                description=flow.UI_TEXT["review_data_description"],
                table_list=table_list,
            )
            consent_result = yield ph.render_page(
                flow.UI_TEXT["review_data_header"], review_prompt
            )

            if consent_result.__type__ == "PayloadJSON":
                logger.info("Data donated for %s", platform_name)
                yield ph.donate(f"{session_id}-{platform_name.lower()}", consent_result.value)
            elif consent_result.__type__ == "PayloadFalse":
                yield ph.donate(
                    f"{session_id}-{platform_name.lower()}",
                    json.dumps({"status": "donation declined"}),
                )

    logger.info("All platforms complete")
    yield ph.exit(0, "Success")
