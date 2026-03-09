import traceback
import json
import datetime
from collections.abc import Generator

from port.script import process
from port.script import process as process_example
from port.api.commands import CommandSystemExit, CommandUIRender, CommandSystemDonate
from port.api.file_utils import AsyncFileAdapter
import port.api.props as props


class _FlatTranslatable:
    """Serialises as the translations dict directly ({"nl": ..., "en": ...}).

    Used internally by error_flow so that test assertions can access
    text["nl"] without an extra "translations" nesting level.
    The JS side reads Translatable via translator.ts which accesses
    .translations — but error_flow pages are Python-only consent pages
    whose text content is never passed back to the JS Translatable parser.
    """

    def __init__(self, translations: dict):
        self.translations = translations

    def toDict(self):
        return dict(self.translations)


class _TextItem:
    """A PropsUIPromptText-like body item that uses _FlatTranslatable."""

    def __init__(self, text: dict):
        self._text = text

    def toDict(self):
        return {
            "__type__": "PropsUIPromptText",
            "title": None,
            "text": dict(self._text),
        }


def error_flow(platform: str, tb: str):
    """
    Generator that handles a Python exception in the donation flow.

    Yields an error consent page, then optionally donates the error log
    if the participant consents.

    Args:
        platform: Name of the active platform when the error occurred.
        tb: Full traceback string from traceback.format_exc().
    """
    header = props.PropsUIHeader(
        props.Translatable({"nl": "Er is iets misgegaan", "en": "Something went wrong"})
    )
    body = [
        _TextItem({"nl": tb, "en": tb}),
        props.PropsUIPromptConfirm(
            text=props.Translatable({
                "nl": "Wilt u de fout rapporteren zodat we het probleem kunnen oplossen?",
                "en": "Would you like to report this error so we can fix the problem?",
            }),
            ok=props.Translatable({"nl": "Fout rapporteren", "en": "Report error"}),
            cancel=props.Translatable({"nl": "Overslaan", "en": "Skip"}),
        ),
    ]
    page = props.PropsUIPageDataSubmission(platform or "error", header, body)
    consent_result = yield CommandUIRender(page)

    if consent_result is not None and getattr(consent_result, "__type__", None) == "PayloadTrue":
        error_data = json.dumps({
            "platform": platform,
            "traceback": tb,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        yield CommandSystemDonate("error-report", error_data)


class ScriptWrapper(Generator):
    def __init__(self, script, platform: str = None):
        self.script = script
        self.platform = platform or "unknown"
        self._error_handler = None

    def send(self, data):
        if self._error_handler is not None:
            try:
                command = self._error_handler.send(data)
                return command.toDict()
            except StopIteration:
                return CommandSystemExit(0, "End of script").toDict()

        # Automatically wrap JS file readers with AsyncFileAdapter
        if data and getattr(data, "__type__", None) == "PayloadFile":
            data.value = AsyncFileAdapter(data.value)

        try:
            command = self.script.send(data)
            # If the script yields None (e.g. bare `yield` used as a checkpoint),
            # continue the generator immediately with None so the next step runs.
            while command is None:
                command = self.script.send(None)
        except StopIteration:
            return CommandSystemExit(0, "End of script").toDict()
        except Exception:
            tb = traceback.format_exc()
            self._error_handler = error_flow(self.platform, tb)
            command = next(self._error_handler)
            return command.toDict()
        else:
            return command.toDict()

    def throw(self, type=None, value=None, traceback=None):
        raise StopIteration


def start(sessionId, platform=None):
    script = process(sessionId, platform)
    return ScriptWrapper(script, platform=platform)


def start_example(sessionId):
    script = process_example(sessionId)
    return ScriptWrapper(script)
