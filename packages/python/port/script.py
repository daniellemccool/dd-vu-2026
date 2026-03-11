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
import port.api.commands as commands
import port.helpers.port_helpers as ph

from port.platforms.flow_builder import _build_error_payload

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

# File safety constants and exceptions
_MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
_CHUNKED_EXPORT_BYTES = 2 * 1024 * 1024 * 1024  # exactly 2 GB — split export sentinel


class FileTooLargeError(Exception):
    """Raised when the donated file exceeds the maximum processable size."""


class ChunkedExportError(Exception):
    """
    Raised when the file is exactly 2 GB, indicating a split export.

    Google Takeout and some other platforms split exports at 2 GB boundaries.
    A file at exactly this size is almost certainly an incomplete chunk.
    """


def handle_donate_result(result) -> bool:
    """
    Inspect the result of a yield ph.donate() call.

    Returns True if result is None (fire-and-forget / D3I mono),
    non-PayloadResponse, or PayloadResponse with success=True.
    Returns False if PayloadResponse with success=False.
    """
    if result is None:
        return True
    if getattr(result, "__type__", None) != "PayloadResponse":
        return True
    return bool(result.value.success)


def check_file_safety(file_obj):
    """
    Check file size before extraction.

    Raises:
        ChunkedExportError: If size is exactly 2 GB.
        FileTooLargeError: If size exceeds _MAX_FILE_BYTES.
    """
    size = file_obj.size

    if size == _CHUNKED_EXPORT_BYTES:
        raise ChunkedExportError(
            f"Dit bestand is precies 2 GB groot. Exportbestanden worden soms "
            f"gesplitst bij 2 GB — dit bestand is waarschijnlijk onvolledig. "
            f"Controleer of u alle exportbestanden heeft. "
            f"(This file is exactly 2 GB. Exports are sometimes split at 2 GB "
            f"boundaries — this file may be incomplete.)"
        )

    size_gb = size / (1024 * 1024 * 1024)
    if size > _MAX_FILE_BYTES:
        raise FileTooLargeError(
            f"Bestand te groot: {size_gb:.1f} GB (maximum: 2 GB). "
            f"Probeer een kleinere export. "
            f"(File too large: {size_gb:.1f} GB, maximum: 2 GB.)"
        )


def donation_failed_flow(
    platform_name: str,
    session_id: str,
    error_text: str = "",
    file_value=None,
):
    """
    Generator: handle a server-side donation failure.

    Sequence:
    1. Auto-donate metadata (no consent) — includes zip diagnostics when available.
    2. Show error consent screen with the error text and Donate/Skip buttons.
    3. If Donate: attempt to donate the error report.
       If that also fails: show a manual fallback screen with the error text.
    4. Return — caller's for-loop continues to the next platform.
    """
    # ------------------------------------------------------------------ #
    # 1. Build and auto-donate metadata without asking for consent         #
    # ------------------------------------------------------------------ #
    metadata: dict = {
        "status": "donation_failed",
        "platform": platform_name,
        "session_id": str(session_id),
    }
    if error_text:
        metadata["error_text"] = error_text

    if file_value is not None:
        try:
            zip_info = _build_error_payload(file_value, platform_name)
            for key in ("zip_size_bytes", "top_level_folders", "detected_format"):
                if key in zip_info:
                    metadata[key] = zip_info[key]
        except Exception:
            pass

    yield ph.donate("error-log", json.dumps(metadata))

    # ------------------------------------------------------------------ #
    # 2. Show consent screen                                               #
    # ------------------------------------------------------------------ #
    error_display = error_text or json.dumps(metadata, indent=2)

    header = props.PropsUIHeader(
        props.Translatable({"nl": "Verzenden mislukt", "en": "Upload failed"})
    )
    body = [
        props.PropsUIPromptText(
            text=props.Translatable({
                "en": (
                    "Unfortunately, we encountered an error. "
                    "You can see the exact error text below. "
                    "We'd like to ask you to donate this error text so that the researchers "
                    "can try to understand what went wrong and fix it.\n\n"
                    "Do you agree to share this error message?"
                ),
                "nl": (
                    "Helaas is er een fout opgetreden. "
                    "U kunt de exacte foutmelding hieronder bekijken. "
                    "We vragen u vriendelijk om deze foutmelding te doneren zodat de onderzoekers "
                    "kunnen begrijpen wat er misgegaan is en het kunnen oplossen.\n\n"
                    "Gaat u akkoord met het delen van deze foutmelding?"
                ),
            })
        ),
        props.PropsUIPromptText(
            text=props.Translatable({"en": error_display, "nl": error_display})
        ),
        props.PropsUIPromptText(
            text=props.Translatable({
                "en": "Do you want to provide context or remove something before sending? "
                      "The error text above will be sent as-is.",
                "nl": "Wilt u context toevoegen of iets verwijderen voor het verzenden? "
                      "De bovenstaande foutmelding wordt zoals die is verzonden.",
            })
        ),
        props.PropsUIPromptConfirm(
            text=props.Translatable({"en": "", "nl": ""}),
            ok=props.Translatable({"en": "Donate", "nl": "Doneer"}),
            cancel=props.Translatable({"en": "Skip", "nl": "Sla over"}),
        ),
    ]
    page = props.PropsUIPageDataSubmission("upload-failed", header, body)
    report_result = yield commands.CommandUIRender(page)

    # ------------------------------------------------------------------ #
    # 3. Handle Donate                                                     #
    # ------------------------------------------------------------------ #
    if report_result.__type__ == "PayloadTrue":
        error_report = {
            "status": "error_report",
            "platform": platform_name,
            "session_id": str(session_id),
            "error_text": error_display,
        }
        donate2_result = yield ph.donate("error-report", json.dumps(error_report))

        if not handle_donate_result(donate2_result):
            # Error report donation also failed — show manual fallback screen
            fallback_header = props.PropsUIHeader(
                props.Translatable({"nl": "Verzenden mislukt", "en": "Upload failed"})
            )
            fallback_body = [
                props.PropsUIPromptText(
                    text=props.Translatable({
                        "en": (
                            "The upload failed. You can help us by contacting the researcher "
                            "with the error message that was generated:"
                        ),
                        "nl": (
                            "Het verzenden is mislukt. U kunt ons helpen door contact op te nemen "
                            "met de onderzoeker met de volgende foutmelding:"
                        ),
                    })
                ),
                props.PropsUIPromptText(
                    text=props.Translatable({"en": error_display, "nl": error_display})
                ),
                props.PropsUIPromptConfirm(
                    text=props.Translatable({"en": "", "nl": ""}),
                    ok=props.Translatable({"en": "Okay", "nl": "Oké"}),
                    cancel=props.Translatable({"en": "Close", "nl": "Sluiten"}),
                ),
            ]
            fallback_page = props.PropsUIPageDataSubmission(
                "upload-failed-fallback", fallback_header, fallback_body
            )
            yield commands.CommandUIRender(fallback_page)
    # Skip (PayloadFalse) or done — generator returns; caller continues to next platform


def process(session_id: str, platform: str | None = None):
    logger.info("Starting the donation flow for session %s", session_id)

    all_platforms = [
        ("LinkedIn",  linkedin.LinkedInFlow(session_id)),
        ("Instagram", instagram.InstagramFlow(session_id)),
        ("Chrome",    chrome.ChromeFlow(session_id)),
        ("Facebook",  facebook.FacebookFlow(session_id)),
        ("YouTube",   youtube.YouTubeFlow(session_id)),
        ("TikTok",    tiktok.TikTokFlow(session_id)),
        ("X",         x.XFlow(session_id)),
    ]

    if platform and platform not in ("undefined", ""):
        platforms = [(name, flow) for name, flow in all_platforms if name.lower() == platform.lower()]
        if not platforms:
            logger.warning("Unknown platform '%s', running all platforms", platform)
            platforms = all_platforms
        else:
            logger.info("Running single-platform build for: %s", platform)
    else:
        platforms = all_platforms

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
                check_file_safety(file_result.value)  # raises FileTooLargeError or ChunkedExportError
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
                donate_result = yield ph.donate(
                    f"{session_id}-{platform_name.lower()}", consent_result.value
                )
                if not handle_donate_result(donate_result):
                    logger.error("Donation failed for %s", platform_name)
                    error_text = str(
                        getattr(getattr(donate_result, "value", None), "error", "") or ""
                    )
                    yield from donation_failed_flow(
                        platform_name,
                        str(session_id),
                        error_text=error_text,
                        file_value=getattr(file_result, "value", None),
                    )
                    # No return — the for-loop continues to the next platform
            elif consent_result.__type__ == "PayloadFalse":
                yield ph.donate(
                    f"{session_id}-{platform_name.lower()}",
                    json.dumps({"status": "donation declined"}),
                )
                # decline donations are fire-and-forget; ignore result

    logger.info("All platforms complete")
    yield commands.CommandUIRender(props.PropsUIPageEnd())
