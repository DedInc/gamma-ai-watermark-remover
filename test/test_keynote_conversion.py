"""
Pytest tests for Keynote ↔ PPTX conversion.

These tests drive the real Keynote.app via AppleScript and are therefore
macOS-only.  On any other platform the entire module is skipped automatically.

Run with:  pytest test/test_keynote_conversion.py -v  (macOS only)
"""
import os
import subprocess
import sys

import pytest

# Skip the whole module on non-macOS systems
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="Keynote conversion requires macOS and Keynote.app"
)

from processors.keynote.converter import key_to_pptx, pptx_to_key  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_dummy_keynote(output_path: str) -> None:
    """Create a minimal Keynote document via AppleScript."""
    escaped = output_path.replace("\\", "\\\\").replace('"', '\\"')
    script = f"""
tell application "Keynote"
    activate
    set theDoc to make new document
    delay 1
    save theDoc in POSIX file "{escaped}"
    close theDoc saving no
end tell
"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"AppleScript failed to create dummy Keynote file:\n{result.stderr or result.stdout}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_key_to_pptx(tmp_path):
    """key_to_pptx() should produce a .pptx file from a .key file."""
    key_path  = str(tmp_path / "dummy.key")
    pptx_path = str(tmp_path / "dummy.pptx")

    _create_dummy_keynote(key_path)
    assert os.path.exists(key_path), "Dummy .key file was not created by AppleScript"

    result = key_to_pptx(key_path, pptx_path)
    assert result["success"] is True, f"key_to_pptx failed: {result.get('error')}"
    assert os.path.isfile(pptx_path), ".pptx output file was not created"


def test_pptx_to_key(tmp_path):
    """pptx_to_key() should produce a .key file from a .pptx file."""
    key_path       = str(tmp_path / "dummy.key")
    pptx_path      = str(tmp_path / "dummy.pptx")
    back_key_path  = str(tmp_path / "dummy_back.key")

    _create_dummy_keynote(key_path)

    # Assert the first conversion step so failures here produce clear diagnostics.
    r1 = key_to_pptx(key_path, pptx_path)
    assert r1["success"] is True, f"key_to_pptx (prerequisite) failed: {r1.get('error')}"
    assert os.path.isfile(pptx_path), ".pptx prerequisite file was not created"

    result = pptx_to_key(pptx_path, back_key_path)
    assert result["success"] is True, f"pptx_to_key failed: {result.get('error')}"
    assert os.path.exists(back_key_path), ".key output file was not created"


def test_full_roundtrip(tmp_path):
    """A full .key → .pptx → .key round-trip should succeed end-to-end."""
    key_path       = str(tmp_path / "roundtrip.key")
    pptx_path      = str(tmp_path / "roundtrip.pptx")
    back_key_path  = str(tmp_path / "roundtrip_back.key")

    _create_dummy_keynote(key_path)

    r1 = key_to_pptx(key_path, pptx_path)
    assert r1["success"], f"key_to_pptx step failed: {r1.get('error')}"

    r2 = pptx_to_key(pptx_path, back_key_path)
    assert r2["success"], f"pptx_to_key step failed: {r2.get('error')}"

    assert os.path.exists(back_key_path)
