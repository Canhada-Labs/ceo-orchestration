"""Sample script that mentions CEO_DETECTOR_1_TEST in a comment but
does NOT actually read it via os.environ / os.getenv / subprocess.run.

Comments + docstrings should not count as runtime reads.
"""

import os


def some_func() -> str:
    # CEO_DETECTOR_1_TEST is mentioned here but we read SOMETHING_ELSE
    return os.environ.get("SOMETHING_ELSE", "")
