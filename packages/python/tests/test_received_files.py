"""
Validation of received donation files is handled by the interactive script:

    poetry run python tests/validate_received.py \
        --received-dir ~/data/d3i/test_packages/port-vu/received_files/<date>

The script discovers which platforms are present, asks for the expected outcome
per platform (consent / consent-with-change / decline), and validates accordingly.

NOTE ON TEST DATA AVAILABILITY
-------------------------------
These tests require two things that are not checked into the repository and
cannot be shared:

1. The received files directory -- JSON output written by the Eyra platform to
   the researcher's local storage after a live or preview session. Location on
   dmm's machine: ~/data/d3i/test_packages/port-vu/received_files/<date>/

2. The originating DDPs -- the participant's original data export zip files
   (e.g. Complete_LinkedInDataExport_*.zip, twitter-*.zip) that were uploaded
   during the session. Location: ~/data/d3i/test_packages/port-vu/

Both contain personal data and are never committed.

NOTE ON ONBOARDING FILES
------------------------
*-onboarding.json files are only generated on a participant's FIRST session per
assignment (or after a consent document revision). Eyra's crew_page.ex skips
the consent step for preview/tester users who already signed the current
revision. The validate_received.py script handles this automatically.
"""
