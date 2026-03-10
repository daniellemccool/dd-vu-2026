"""
Tests for Facebook DDP error handling helpers.

sys.modules['js'] mock required for Pyodide-only import in file_utils.
"""
import sys
import io
import zipfile

from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

from port.platforms.flow_builder import _build_error_payload


def _make_zip(entries: list[str]) -> io.BytesIO:
    """Create an in-memory zip with empty files at the given paths."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for entry in entries:
            zf.writestr(entry, b"")
    buf.seek(0)
    return buf


def test_build_error_payload_html_export():
    """Zip with >50% .html files is detected as html_export."""
    entries = [f"export/file{i}.html" for i in range(8)] + ["export/readme.txt", "export/data.json"]
    buf = _make_zip(entries)
    payload = _build_error_payload(buf, "Facebook")
    assert payload["detected_format"] == "html_export"
    assert payload["status"] == "file_format_not_supported"
    assert payload["platform"] == "Facebook"
    assert payload["zip_size_bytes"] > 0
    assert "export" in payload["top_level_folders"]


def test_build_error_payload_data_logs():
    """Zip with data_logs/ prefix is detected as data_logs_json."""
    entries = [
        "data_logs/content/0/page_1.json",
        "data_logs/content/1/page_1.json",
        "readme.txt",
    ]
    buf = _make_zip(entries)
    payload = _build_error_payload(buf, "Facebook")
    assert payload["detected_format"] == "data_logs_json"
    assert sorted(payload["top_level_folders"]) == ["data_logs", "readme.txt"]


def test_build_error_payload_unknown():
    """Zip with mixed non-HTML files is detected as unknown."""
    entries = ["some_folder/file.json", "some_folder/other.csv"]
    buf = _make_zip(entries)
    payload = _build_error_payload(buf, "Facebook")
    assert payload["detected_format"] == "unknown"


def test_build_error_payload_top_level_folders_deduped():
    """top_level_folders contains unique top-level entries, sorted."""
    entries = [
        "folderA/a.json",
        "folderA/b.json",
        "folderB/c.json",
        "readme.txt",
    ]
    buf = _make_zip(entries)
    payload = _build_error_payload(buf, "TestPlatform")
    assert payload["top_level_folders"] == ["folderA", "folderB", "readme.txt"]


def test_build_error_payload_exactly_50pct_html_is_not_html_export():
    """Exactly 50% HTML does NOT trigger html_export (requires >50%)."""
    entries = ["a.html", "b.html", "c.json", "d.json"]
    buf = _make_zip(entries)
    payload = _build_error_payload(buf, "Facebook")
    assert payload["detected_format"] != "html_export"


def test_build_error_payload_empty_zip():
    """Empty zip (zero entries) returns detected_format='unknown' and empty top_level_folders."""
    buf = _make_zip([])
    payload = _build_error_payload(buf, "Facebook")
    assert payload["detected_format"] == "unknown"
    assert payload["top_level_folders"] == []


from port.platforms.facebook import last_28_days_to_df


def test_last_28_days_returns_empty_when_file_missing():
    """No spurious rows when the expected JSON file is absent from the zip."""
    # Zip with no matching file
    buf = _make_zip(["some_other_file.json"])
    result = last_28_days_to_df(buf)  # type: ignore[arg-type]  # BytesIO accepted at runtime via extract_file_from_zip
    assert result.empty, f"Expected empty DataFrame, got {len(result)} rows"
