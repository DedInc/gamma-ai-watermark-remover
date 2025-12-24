"""XML structure analysis for PPTX files."""

import os
import zipfile
import xml.etree.ElementTree as ET


def extract_and_analyze_xml(pptx_path):
    """Extract PPTX as ZIP and analyze XML structure."""
    result = []
    result.append("\n" + "=" * 80)
    result.append("XML STRUCTURE ANALYSIS")
    result.append("=" * 80)

    # Create extraction directory
    extract_dir = "pptx_extracted"

    # Unzip the PPTX
    with zipfile.ZipFile(pptx_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    result.append(f"\nExtracted to: {extract_dir}")
    result.append("\nDirectory structure:")

    for root, dirs, files in os.walk(extract_dir):
        level = root.replace(extract_dir, "").count(os.sep)
        indent = "  " * level
        result.append(f"{indent}{os.path.basename(root)}/")
        subindent = "  " * (level + 1)
        for file in files:
            result.append(f"{subindent}{file}")

    # Look for gamma-related content in XML files
    result.extend(_search_gamma_in_xml(extract_dir))

    # Analyze slide XML files for shape details
    result.extend(_analyze_slide_xml(extract_dir))

    # Check relationships files for hyperlinks
    result.extend(_analyze_relationships(extract_dir))

    return result


def _search_gamma_in_xml(extract_dir):
    """Search for 'gamma' in XML files."""
    result = []
    result.append("\n" + "-" * 40)
    result.append("SEARCHING FOR 'GAMMA' IN XML FILES:")
    result.append("-" * 40)

    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".xml") or file.endswith(".rels"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "gamma" in content.lower():
                            result.append(f"\n*** FOUND 'gamma' in: {filepath} ***")
                            # Find the lines containing gamma
                            for i, line in enumerate(content.split("\n")):
                                if "gamma" in line.lower():
                                    result.append(f"  Line {i + 1}: {line[:200]}...")
                except Exception:
                    pass

    return result


def _analyze_slide_xml(extract_dir):
    """Analyze slide XML files for shape details."""
    result = []
    result.append("\n" + "-" * 40)
    result.append("ANALYZING SLIDE XML STRUCTURE:")
    result.append("-" * 40)

    slides_dir = os.path.join(extract_dir, "ppt", "slides")
    if os.path.exists(slides_dir):
        for slide_file in sorted(os.listdir(slides_dir)):
            if slide_file.endswith(".xml"):
                filepath = os.path.join(slides_dir, slide_file)
                result.append(f"\n{slide_file}:")
                try:
                    tree = ET.parse(filepath)
                    root_elem = tree.getroot()

                    # Find all shapes with hyperlinks
                    for elem in root_elem.iter():
                        if "hlinkClick" in elem.tag or "hlink" in elem.tag.lower():
                            result.append(f"  Hyperlink element: {elem.tag}")
                            result.append(f"    Attributes: {elem.attrib}")
                        if elem.text and "gamma" in str(elem.text).lower():
                            result.append(f"  Text containing 'gamma': {elem.text}")

                except Exception as e:
                    result.append(f"  Error parsing: {e}")

    return result


def _analyze_relationships(extract_dir):
    """Analyze relationships files for hyperlinks."""
    result = []
    result.append("\n" + "-" * 40)
    result.append("ANALYZING RELATIONSHIPS FILES:")
    result.append("-" * 40)

    rels_paths = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".rels"):
                rels_paths.append(os.path.join(root, file))

    for rels_path in rels_paths:
        try:
            tree = ET.parse(rels_path)
            root_elem = tree.getroot()
            has_external = False

            for rel in root_elem:
                target = rel.get("Target", "")
                rel_type = rel.get("Type", "")
                target_mode = rel.get("TargetMode", "")

                if "gamma" in target.lower() or target_mode == "External":
                    if not has_external:
                        result.append(f"\n{rels_path}:")
                        has_external = True
                    result.append(
                        f"  Relationship: Type={rel_type.split('/')[-1]}, "
                        f"Target={target}, Mode={target_mode}"
                    )
                    if "gamma" in target.lower():
                        result.append("    *** GAMMA HYPERLINK FOUND ***")
        except Exception:
            pass

    return result
