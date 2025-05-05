import fitz
from PIL import Image
import io
import numpy as np
import os
from config import WatermarkConfig

class WatermarkDetector:
    def __init__(self, template_histogram=None, inverted_template_histogram=None, similarity_threshold=WatermarkConfig.SIMILARITY_THRESHOLD, similarity_inverted_threshold=WatermarkConfig.SIMILARITY_INVERTED_THRESHOLD):
        self.template_histogram = template_histogram if template_histogram else WatermarkConfig.get_template_histogram_array()
        self.inverted_template_histogram = inverted_template_histogram if inverted_template_histogram else np.array(WatermarkConfig.INVERTED_TEMPLATE_HISTOGRAM)
        self.similarity_threshold = similarity_threshold
        self.similarity_inverted_threshold = similarity_inverted_threshold

    def calculate_histogram(self, image_data):
        img = Image.open(io.BytesIO(image_data)).convert('L')
        hist, _ = np.histogram(img, bins=256, range=(0, 256))
        return hist / np.sum(hist)

    def compare_histograms(self, hist1, hist2):
        intersection = np.minimum(hist1, hist2).sum()
        similarity = intersection / np.sum(hist1)
        return similarity

    def identify_watermarks(self, pdf_path):
        images_to_remove_info = []
        extracted_dir = 'extracted_images'
        os.makedirs(extracted_dir, exist_ok=True)
        try:
            pdf_document = fitz.open(pdf_path)
            print("\nSearching for watermarks...\n")
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                image_list = page.get_images(full=True)

                for img_info_tuple in image_list:
                    xref = img_info_tuple[0]
                    img_index = img_info_tuple[1]

                    try:
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        if image_bytes:
                            # Save every extracted image for inspection
                            ext = base_image.get('ext', 'png')
                            out_path = os.path.join(extracted_dir, f"page{page_num+1}_xref{xref}_img{img_index}.{ext}")
                            with open(out_path, 'wb') as f:
                                f.write(image_bytes)
                            # Print image properties for targeting
                            img = Image.open(io.BytesIO(image_bytes))
                            print(f"Extracted image: {out_path}, size: {img.width}x{img.height}, ext: {ext}")

                            current_hist = self.calculate_histogram(image_bytes)

                            similarity = self.compare_histograms(self.template_histogram, current_hist)
                            inverted_similarity = self.compare_histograms(self.inverted_template_histogram, current_hist)

                            print(f"  Similarity (normal) of image xref:{xref} on page {page_num + 1}: {similarity * 100:.2f}%")
                            print(f"  Similarity (inverted) of image xref:{xref} on page {page_num + 1}: {inverted_similarity * 100:.2f}%")

                            is_watermark = False
                            if similarity >= self.similarity_threshold:
                                print(f"  - Normal similarity exceeds threshold ({self.similarity_threshold * 100:.0f}%)")
                                is_watermark = True
                                final_similarity = similarity
                            if inverted_similarity >= self.similarity_inverted_threshold:
                                print(f"  - Inverted similarity exceeds threshold ({self.similarity_inverted_threshold * 100:.0f}%)")
                                is_watermark = True
                                final_similarity = inverted_similarity 

                            # Badge detection by size and extension
                            if img.width == 575 and img.height == 137 and ext == 'png':
                                print(f"[AUTO] Badge candidate detected by size/ext: {out_path}")
                                image_name = f"Image_{img_index}.{ext}"
                                images_to_remove_info.append({
                                    'page': page_num,
                                    'xref': xref,
                                    'image_name': image_name,
                                    'similarity': 1.0
                                })
                                continue

                            if is_watermark:
                                image_name = f"Image_{img_index}.{base_image['ext']}"
                                images_to_remove_info.append({
                                    'page': page_num,
                                    'xref': xref,
                                    'image_name': image_name,
                                    'similarity': final_similarity 
                                })
                                print(f"Watermark candidate found on page {page_num + 1}:")
                                print(f"  Image name: {image_name}, xref: {xref}")
                                print(f"  Similarity to watermark template: {final_similarity * 100:.2f}%")
                                print("-" * 50)
                            else:
                                print("  Not a watermark based on both normal and inverted histograms.")
                                print("-" * 50)

                        else:
                            print(f"  - Error: Could not get image bytes for xref {xref} on page {page_num + 1}.")

                    except Exception as inner_e:
                        print(f"Error processing image xref {xref} on page {page_num + 1}: {inner_e}")

            pdf_document.close()

            if not images_to_remove_info:
                print(f"No watermarks found with thresholds (normal: {self.similarity_threshold * 100:.0f}%, inverted: {self.similarity_inverted_threshold * 100:.0f}%) in PDF.")
            return images_to_remove_info, None

        except Exception as e:
            return [], f"Error identifying watermarks: {str(e)}"