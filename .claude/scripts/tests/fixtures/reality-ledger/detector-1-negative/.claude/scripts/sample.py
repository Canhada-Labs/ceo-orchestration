"""Sample with a real runtime read of CEO_DETECTOR_1_OK."""

import os
import subprocess


def reader() -> str:
    """Three different forms of read."""
    a = os.environ.get("CEO_DETECTOR_1_OK", "")
    b = os.getenv("CEO_DETECTOR_1_OK")
    subprocess.run(["true"], env={"CEO_DETECTOR_1_OK": "1"})
    return a or (b or "")
