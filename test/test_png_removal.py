import os
import sys
from PIL import Image, ImageDraw

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.processors import PNGProcessor

def create_mock_png(path: str):
    """Create a 400x300 PNG with a solid background and a bottom-right watermark."""
    # Create solid blue image (representing slides background color)
    img = Image.new("RGBA", (400, 300), (45, 90, 180, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw simulated watermark in the bottom-right corner (approx bottom-right 22% width, 10% height)
    # Watermark region: x in [312, 400], y in [270, 300]
    draw.rectangle([320, 275, 390, 295], fill=(255, 255, 255, 255)) # Mock white branding badge
    draw.text((325, 280), "Gamma", fill=(0, 0, 0, 255))
    
    img.save(path, "PNG")
    print(f"Created mock PNG at: {path}")

def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    input_png = os.path.join(test_dir, "test_input.png")
    output_png = os.path.join(test_dir, "test_output.png")
    
    # Clean old files
    for p in [input_png, output_png]:
        if os.path.exists(p):
            os.remove(p)
            
    try:
        create_mock_png(input_png)
        
        # Initialize and process using PNGProcessor
        processor = PNGProcessor()
        print("\n--- Testing PNGProcessor ---")
        res = processor.process(input_png, output_png, "test_input.png")
        print("Result:", res)
        
        if not res["success"] or not os.path.exists(output_png):
            print("Error: PNG watermark removal failed.")
            sys.exit(1)
            
        # Verify that the watermark region was filled with the background color (approx blue)
        cleaned_img = Image.open(output_png).convert("RGBA")
        
        # Sample a pixel inside the watermark region (e.g., 350, 285) which was white in input
        pixel_color = cleaned_img.getpixel((350, 285))
        print(f"Sampled pixel inside cleaned watermark area (350, 285): {pixel_color}")
        
        # Background color is (45, 90, 180, 255). It should match or be close
        if pixel_color[0] == 45 and pixel_color[1] == 90 and pixel_color[2] == 180:
            print("Watermark successfully painted over with background color!")
        else:
            print(f"Warning: Cleaned color {pixel_color} does not match background color (45, 90, 180)!")
            sys.exit(1)
            
        print("\nAll PNG tests passed successfully!")
        
    finally:
        # Cleanup
        for p in [input_png, output_png]:
            if os.path.exists(p):
                os.remove(p)

if __name__ == "__main__":
    main()
