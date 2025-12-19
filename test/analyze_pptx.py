#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPTX Watermark Analysis Script
Analyzes the sample PPTX file to understand Gamma watermark structure.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pptx import Presentation
from pptx.util import Inches, Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
import os
import zipfile
import xml.etree.ElementTree as ET

# Constants
PPTX_FILE = r"Sample\Your-Tenant-Just-Sent-You-This-Photo.pptx"

def emu_to_inches(emu):
    """Convert EMUs to inches"""
    return emu / 914400

def analyze_hyperlinks(shape):
    """Extract hyperlinks from a shape"""
    hyperlinks = []
    
    # Check if the shape itself has a click action (hyperlink)
    if hasattr(shape, 'click_action') and shape.click_action:
        action = shape.click_action
        if hasattr(action, 'hyperlink') and action.hyperlink:
            hyperlinks.append(f"Click action: {action.hyperlink.address}")
    
    # Check for hyperlinks in text frames
    if hasattr(shape, 'text_frame'):
        try:
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if hasattr(run, 'hyperlink') and run.hyperlink:
                        if run.hyperlink.address:
                            hyperlinks.append(f"Text hyperlink: {run.hyperlink.address}")
        except:
            pass
    
    return hyperlinks

def get_shape_position_percentage(shape, slide_width, slide_height):
    """Calculate shape position as percentage of slide dimensions"""
    if shape.left is None or shape.top is None:
        return None, None, None, None
    
    left_pct = (shape.left / slide_width) * 100
    top_pct = (shape.top / slide_height) * 100
    right_pct = ((shape.left + shape.width) / slide_width) * 100 if shape.width else left_pct
    bottom_pct = ((shape.top + shape.height) / slide_height) * 100 if shape.height else top_pct
    
    return left_pct, top_pct, right_pct, bottom_pct

def is_bottom_right_corner(shape, slide_width, slide_height, threshold=70):
    """Check if shape is in bottom-right corner (>threshold% of dimensions)"""
    left_pct, top_pct, right_pct, bottom_pct = get_shape_position_percentage(shape, slide_width, slide_height)
    if left_pct is None:
        return False
    return left_pct >= threshold and top_pct >= threshold

def analyze_shape(shape, slide_width, slide_height, indent=0):
    """Analyze a single shape and return details"""
    prefix = "  " * indent
    result = []
    
    # Get shape type
    shape_type = "Unknown"
    if hasattr(shape, 'shape_type'):
        shape_type = str(shape.shape_type)
    
    # Get position
    left = shape.left if shape.left is not None else 0
    top = shape.top if shape.top is not None else 0
    width = shape.width if shape.width is not None else 0
    height = shape.height if shape.height is not None else 0
    
    left_pct, top_pct, right_pct, bottom_pct = get_shape_position_percentage(shape, slide_width, slide_height)
    
    result.append(f"{prefix}Shape: {shape.name}")
    result.append(f"{prefix}  Type: {shape_type}")
    result.append(f"{prefix}  Position (EMUs): left={left}, top={top}, width={width}, height={height}")
    result.append(f"{prefix}  Position (inches): left={emu_to_inches(left):.2f}\", top={emu_to_inches(top):.2f}\", width={emu_to_inches(width):.2f}\", height={emu_to_inches(height):.2f}\"")
    
    if left_pct is not None:
        result.append(f"{prefix}  Position (%): left={left_pct:.1f}%, top={top_pct:.1f}%, right={right_pct:.1f}%, bottom={bottom_pct:.1f}%")
    
    # Check if in bottom-right corner
    if is_bottom_right_corner(shape, slide_width, slide_height, 70):
        result.append(f"{prefix}  *** BOTTOM-RIGHT CORNER (>70%) ***")
    
    # Get text content
    if hasattr(shape, 'text') and shape.text:
        text = shape.text[:100] + "..." if len(shape.text) > 100 else shape.text
        result.append(f"{prefix}  Text: '{text}'")
        if 'gamma' in shape.text.lower():
            result.append(f"{prefix}  *** CONTAINS 'GAMMA' IN TEXT ***")
    
    # Get hyperlinks
    hyperlinks = analyze_hyperlinks(shape)
    if hyperlinks:
        for link in hyperlinks:
            result.append(f"{prefix}  Hyperlink: {link}")
            if 'gamma' in link.lower():
                result.append(f"{prefix}  *** CONTAINS 'GAMMA' IN HYPERLINK ***")
    
    # Check for image
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        result.append(f"{prefix}  *** THIS IS AN IMAGE ***")
        try:
            if hasattr(shape, 'image'):
                result.append(f"{prefix}  Image format: {shape.image.content_type}")
                result.append(f"{prefix}  Image size: {len(shape.image.blob)} bytes")
        except Exception as e:
            result.append(f"{prefix}  Image info error: {e}")
    
    # Handle group shapes
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        result.append(f"{prefix}  *** THIS IS A GROUP SHAPE ***")
        for subshape in shape.shapes:
            result.extend(analyze_shape(subshape, slide_width, slide_height, indent + 1))
    
    return result

def analyze_slide_layout(layout, slide_width, slide_height):
    """Analyze a slide layout"""
    result = []
    result.append(f"\n  Layout: {layout.name}")
    
    for shape in layout.shapes:
        result.extend(analyze_shape(shape, slide_width, slide_height, indent=2))
    
    return result

def analyze_slide_master(master, slide_width, slide_height):
    """Analyze a slide master"""
    result = []
    result.append(f"\nSlide Master: {master.name if hasattr(master, 'name') else 'Unnamed'}")
    
    # Analyze shapes on the master
    for shape in master.shapes:
        result.extend(analyze_shape(shape, slide_width, slide_height, indent=1))
    
    # Analyze layouts
    result.append("\n  Slide Layouts:")
    for layout in master.slide_layouts:
        result.extend(analyze_slide_layout(layout, slide_width, slide_height))
    
    return result

def extract_and_analyze_xml(pptx_path):
    """Extract PPTX as ZIP and analyze XML structure"""
    result = []
    result.append("\n" + "="*80)
    result.append("XML STRUCTURE ANALYSIS")
    result.append("="*80)
    
    # Create extraction directory
    extract_dir = "pptx_extracted"
    
    # Unzip the PPTX
    with zipfile.ZipFile(pptx_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    result.append(f"\nExtracted to: {extract_dir}")
    result.append("\nDirectory structure:")
    
    for root, dirs, files in os.walk(extract_dir):
        level = root.replace(extract_dir, '').count(os.sep)
        indent = '  ' * level
        result.append(f"{indent}{os.path.basename(root)}/")
        subindent = '  ' * (level + 1)
        for file in files:
            result.append(f"{subindent}{file}")
    
    # Look for gamma-related content in XML files
    result.append("\n" + "-"*40)
    result.append("SEARCHING FOR 'GAMMA' IN XML FILES:")
    result.append("-"*40)
    
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xml') or file.endswith('.rels'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'gamma' in content.lower():
                            result.append(f"\n*** FOUND 'gamma' in: {filepath} ***")
                            # Find the lines containing gamma
                            for i, line in enumerate(content.split('\n')):
                                if 'gamma' in line.lower():
                                    result.append(f"  Line {i+1}: {line[:200]}...")
                except Exception as e:
                    pass
    
    # Analyze slide XML files for shape details
    result.append("\n" + "-"*40)
    result.append("ANALYZING SLIDE XML STRUCTURE:")
    result.append("-"*40)
    
    slides_dir = os.path.join(extract_dir, "ppt", "slides")
    if os.path.exists(slides_dir):
        for slide_file in sorted(os.listdir(slides_dir)):
            if slide_file.endswith('.xml'):
                filepath = os.path.join(slides_dir, slide_file)
                result.append(f"\n{slide_file}:")
                try:
                    tree = ET.parse(filepath)
                    root_elem = tree.getroot()
                    
                    # Register namespaces
                    namespaces = {
                        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
                        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
                    }
                    
                    # Find all shapes with hyperlinks
                    for elem in root_elem.iter():
                        if 'hlinkClick' in elem.tag or 'hlink' in elem.tag.lower():
                            result.append(f"  Hyperlink element: {elem.tag}")
                            result.append(f"    Attributes: {elem.attrib}")
                        if elem.text and 'gamma' in str(elem.text).lower():
                            result.append(f"  Text containing 'gamma': {elem.text}")
                
                except Exception as e:
                    result.append(f"  Error parsing: {e}")
    
    # Check relationships files for hyperlinks
    result.append("\n" + "-"*40)
    result.append("ANALYZING RELATIONSHIPS FILES:")
    result.append("-"*40)
    
    rels_paths = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.rels'):
                rels_paths.append(os.path.join(root, file))
    
    for rels_path in rels_paths:
        try:
            tree = ET.parse(rels_path)
            root_elem = tree.getroot()
            has_external = False
            
            for rel in root_elem:
                target = rel.get('Target', '')
                rel_type = rel.get('Type', '')
                target_mode = rel.get('TargetMode', '')
                
                if 'gamma' in target.lower() or target_mode == 'External':
                    if not has_external:
                        result.append(f"\n{rels_path}:")
                        has_external = True
                    result.append(f"  Relationship: Type={rel_type.split('/')[-1]}, Target={target}, Mode={target_mode}")
                    if 'gamma' in target.lower():
                        result.append(f"    *** GAMMA HYPERLINK FOUND ***")
        except Exception as e:
            pass
    
    return result

def main():
    print("="*80)
    print("GAMMA PPTX WATERMARK ANALYSIS")
    print("="*80)
    print(f"\nAnalyzing file: {PPTX_FILE}")
    
    # Open the presentation
    prs = Presentation(PPTX_FILE)
    
    # Get slide dimensions
    slide_width = prs.slide_width
    slide_height = prs.slide_height
    
    print(f"\nSlide dimensions:")
    print(f"  Width: {slide_width} EMUs ({emu_to_inches(slide_width):.2f} inches)")
    print(f"  Height: {slide_height} EMUs ({emu_to_inches(slide_height):.2f} inches)")
    print(f"  Aspect ratio: {emu_to_inches(slide_width)/emu_to_inches(slide_height):.2f}:1")
    
    # Analyze slides
    print("\n" + "="*80)
    print("SLIDE ANALYSIS")
    print("="*80)
    
    gamma_shapes = []
    
    for i, slide in enumerate(prs.slides):
        print(f"\n--- Slide {i+1} ---")
        print(f"Slide layout: {slide.slide_layout.name}")
        print(f"Number of shapes: {len(slide.shapes)}")
        
        for shape in slide.shapes:
            lines = analyze_shape(shape, slide_width, slide_height, indent=0)
            for line in lines:
                print(line)
            
            # Track gamma-related shapes
            if hasattr(shape, 'text') and 'gamma' in shape.text.lower():
                gamma_shapes.append((f"Slide {i+1}", shape, "text"))
            
            hyperlinks = analyze_hyperlinks(shape)
            for link in hyperlinks:
                if 'gamma' in link.lower():
                    gamma_shapes.append((f"Slide {i+1}", shape, f"hyperlink: {link}"))
            
            # Check if in corner
            if is_bottom_right_corner(shape, slide_width, slide_height, 70):
                gamma_shapes.append((f"Slide {i+1}", shape, "corner position"))
    
    # Analyze slide masters
    print("\n" + "="*80)
    print("SLIDE MASTER ANALYSIS")
    print("="*80)
    
    for master in prs.slide_masters:
        lines = analyze_slide_master(master, slide_width, slide_height)
        for line in lines:
            print(line)
    
    # Extract and analyze XML
    xml_results = extract_and_analyze_xml(PPTX_FILE)
    for line in xml_results:
        print(line)
    
    # Summary
    print("\n" + "="*80)
    print("WATERMARK DETECTION SUMMARY")
    print("="*80)
    
    if gamma_shapes:
        print("\nPotential watermark shapes found:")
        for location, shape, reason in gamma_shapes:
            print(f"  - {location}: '{shape.name}' ({reason})")
            if shape.left is not None:
                left_pct, top_pct, right_pct, bottom_pct = get_shape_position_percentage(shape, slide_width, slide_height)
                print(f"    Position: {left_pct:.1f}%-{right_pct:.1f}% horizontal, {top_pct:.1f}%-{bottom_pct:.1f}% vertical")
    else:
        print("\nNo obvious gamma watermark shapes found in slides.")
        print("Watermark may be in slide masters, layouts, or embedded differently.")

if __name__ == "__main__":
    main()
