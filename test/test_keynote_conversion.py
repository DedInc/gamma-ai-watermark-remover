import os
import sys
import subprocess

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from processors.keynote.converter import key_to_pptx, pptx_to_key

def create_dummy_keynote(output_path: str):
    """Tell Keynote via AppleScript to create a new document and save it."""
    escaped_path = output_path.replace('\\', '\\\\').replace('"', '\\"')
    script = f'''
tell application "Keynote"
    activate
    set theDoc to make new document
    delay 1
    save theDoc in POSIX file "{escaped_path}"
    close theDoc saving no
end tell
'''
    print(f"Creating dummy Keynote file at: {output_path}")
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print("Failed to create dummy Keynote file:")
        print(result.stderr or result.stdout)
        return False
    return True

def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(test_dir, "test_dummy.key")
    pptx_path = os.path.join(test_dir, "test_dummy.pptx")
    back_key_path = os.path.join(test_dir, "test_dummy_back.key")

    # Clean up old test files
    for path in [key_path, pptx_path, back_key_path]:
        if os.path.exists(path):
            os.remove(path)

    # 1. Create dummy Keynote document
    if not create_dummy_keynote(key_path):
        sys.exit(1)

    if not os.path.exists(key_path):
        print(f"Error: dummy Keynote file was not created at {key_path}")
        sys.exit(1)
    print("Successfully created dummy Keynote file.")

    # 2. Convert to PPTX
    print("\n--- Testing key_to_pptx ---")
    res = key_to_pptx(key_path, pptx_path)
    print("Result:", res)
    if not res["success"] or not os.path.exists(pptx_path):
        print("Error: key_to_pptx failed.")
        sys.exit(1)
    print("Successfully converted Keynote to PPTX.")

    # 3. Convert back to Keynote
    print("\n--- Testing pptx_to_key ---")
    res = pptx_to_key(pptx_path, back_key_path)
    print("Result:", res)
    if not res["success"] or not os.path.exists(back_key_path):
        print("Error: pptx_to_key failed.")
        sys.exit(1)
    print("Successfully converted PPTX back to Keynote.")

    print("\nAll Keynote tests passed successfully!")

    # Clean up files
    for path in [key_path, pptx_path, back_key_path]:
        if os.path.exists(path):
            os.remove(path)

if __name__ == "__main__":
    main()
