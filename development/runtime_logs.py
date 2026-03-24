# Necessary imports
import builtins
from collections import deque
from datetime import datetime



# In-memory rolling log buffer to store recent console output
_LOG_BUFFER: deque[str] = deque(maxlen=5000)
_PRINT_HOOK_INSTALLED = False
_ORIGINAL_PRINT = builtins.print


# Installs hook to capture print output
def install_print_hook() -> None:
    """Mirror console print output into an in-memory rolling log buffer."""
    global _PRINT_HOOK_INSTALLED
    if _PRINT_HOOK_INSTALLED:
        return

    def _hooked_print(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")

        try:
            rendered = sep.join(str(arg) for arg in args)
        except Exception:
            rendered = ""

        if end is not None:
            rendered = f"{rendered}{end}"

        timestamp = datetime.now().strftime("%H:%M:%S")
        lines = rendered.rstrip("\n").splitlines()
        for line in lines:
            if line:
                _LOG_BUFFER.append(f"[{timestamp}] {line}")

        _ORIGINAL_PRINT(*args, **kwargs)

    builtins.print = _hooked_print
    _PRINT_HOOK_INSTALLED = True


# Retrieves recent logs
def get_recent_logs(limit: int = 300) -> list[str]:
    if limit <= 0:
        return []
    snapshot = list(_LOG_BUFFER)
    return snapshot[-limit:]