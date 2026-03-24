# Necessary imports
import os


# Directory paths and in-memory state for active panels
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BANNER_PATH = os.path.join(BASE_DIR, "attachments", "banner.png")
ACTIVE_DEV_PANELS: dict[int, dict[str, int]] = {}
ACTIVE_PERMS_PANELS: dict[int, dict[str, int]] = {}