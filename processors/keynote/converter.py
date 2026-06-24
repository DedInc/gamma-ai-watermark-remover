"""
Keynote ↔ PPTX Converter (macOS only).

Uses AppleScript via `osascript` to drive the Keynote application for format
conversion.  This is the only reliable approach for .key files because the
format is a proprietary compressed binary (ZIP + Snappy-compressed protobufs).

Flow for removing watermarks from a .key file:
  1.  key_to_pptx(key_path, pptx_path)  — open in Keynote, export as PPTX
  2.  [PPTXWatermarkRemover cleans the PPTX in Python]
  3.  pptx_to_key(pptx_path, key_path)  — open cleaned PPTX in Keynote, save as .key
"""

import logging
import os
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)

# Serialise all Keynote AppleScript sessions to prevent concurrent interleaving
_KEYNOTE_LOCK = threading.Lock()


def _is_keynote_available() -> bool:
    """Check whether Keynote.app is installed on this Mac.

    Returns False immediately on non-macOS platforms so callers can
    surface a clear, accurate error rather than 'Keynote not installed'.
    """
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["osascript", "-e", 'id of application "Keynote"'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "keynote" in result.stdout.lower()
    except Exception:
        return False


def _escape_applescript_path(path: str) -> str:
    """Escape a path for use in AppleScript double-quoted string literals."""
    escaped = path.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def key_to_pptx(key_path: str, pptx_path: str) -> dict:
    """
    Open a .key file in Keynote and export it as .pptx.

    Args:
        key_path:  Absolute path to the source .key file.
        pptx_path: Absolute path where the .pptx should be written.

    Returns:
        dict: { success: bool, error: str|None }
    """
    if sys.platform != "darwin":
        return {
            "success": False,
            "error": "Keynote conversion is only supported on macOS.",
        }
    if not _is_keynote_available():
        return {
            "success": False,
            "error": (
                "Apple Keynote is not installed. Please install Keynote from "
                "the App Store, or export your presentation as .pptx from "
                "Gamma.app directly."
            ),
        }

    key_path = os.path.abspath(key_path)
    pptx_path = os.path.abspath(pptx_path)

    # Build AppleScript: open the .key file, export as Microsoft PowerPoint, close
    # NOTE: Use stdin piping (not -e flag) to avoid multi-line AppleScript syntax errors
    export_format = "Microsoft PowerPoint"
    script = f"""tell application "Keynote"
    set theDoc to open POSIX file {_escape_applescript_path(key_path)}
    delay 1
    export theDoc to POSIX file {_escape_applescript_path(pptx_path)} as {export_format}
    close theDoc saving no
end tell
"""
    try:
        with _KEYNOTE_LOCK:
            result = subprocess.run(
                ["osascript"], input=script, capture_output=True, text=True, timeout=120
            )
        if result.returncode != 0:
            err = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Unknown AppleScript error"
            )
            logger.error(f"key_to_pptx failed: {err}")
            return {"success": False, "error": f"Keynote conversion failed: {err}"}

        if not os.path.isfile(pptx_path):
            return {
                "success": False,
                "error": "Keynote did not produce a .pptx output file.",
            }

        logger.info(f"key_to_pptx: '{key_path}' → '{pptx_path}'")
        return {"success": True, "error": None}

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Keynote conversion timed out (>120 s). Try a smaller file.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error during Keynote conversion: {e}",
        }


def pptx_to_key(pptx_path: str, key_path: str) -> dict:
    """
    Open a cleaned .pptx in Keynote and save it as a native .key file.

    Args:
        pptx_path: Absolute path to the source .pptx file.
        key_path:  Absolute path where the .key file should be saved.

    Returns:
        dict: { success: bool, error: str|None }
    """
    if sys.platform != "darwin":
        return {
            "success": False,
            "error": "Keynote conversion is only supported on macOS.",
        }
    if not _is_keynote_available():
        return {"success": False, "error": "Apple Keynote is not installed."}

    pptx_path = os.path.abspath(pptx_path)
    key_path = os.path.abspath(key_path)

    # AppleScript: open the PPTX, save it as a native Keynote document, close
    # NOTE: Use stdin piping (not -e flag) to avoid multi-line AppleScript syntax errors
    script = f"""tell application "Keynote"
    set theDoc to open POSIX file {_escape_applescript_path(pptx_path)}
    delay 1
    save theDoc in POSIX file {_escape_applescript_path(key_path)}
    close theDoc saving no
end tell
"""
    try:
        with _KEYNOTE_LOCK:
            result = subprocess.run(
                ["osascript"], input=script, capture_output=True, text=True, timeout=120
            )
        if result.returncode != 0:
            err = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Unknown AppleScript error"
            )
            logger.error(f"pptx_to_key failed: {err}")
            return {"success": False, "error": f"Keynote save failed: {err}"}

        if not os.path.exists(key_path):
            return {
                "success": False,
                "error": "Keynote did not produce a .key output file.",
            }

        logger.info(f"pptx_to_key: '{pptx_path}' → '{key_path}'")
        return {"success": True, "error": None}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Keynote save timed out (>120 s)."}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error saving Keynote file: {e}"}
