import fitz


class WatermarkRemover:
    def __init__(self, target_domain="gamma.app"):
        self.target_domain = target_domain

    def clean_pdf_from_target_domain(self, pdf_path, output_path):
        """Cleans PDF from target domain elements"""

        pdf_document = fitz.open(pdf_path)

        print(f"Processing file: {pdf_path}")
        print(f"Target domain: {self.target_domain}")
        print(f"Number of pages: {len(pdf_document)}")

        total_images_removed = 0
        total_links_removed = 0

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            print(f"\nPage {page_num + 1}:")

            # 1. Remove images in bottom right corner with target links
            images_removed = self._remove_corner_images_with_links(
                page, self.target_domain
            )
            total_images_removed += images_removed

            # 2. Remove all links to target domain
            links_removed = self._remove_all_target_links(page, self.target_domain)
            total_links_removed += links_removed

            if not (images_removed or links_removed):
                print("    No target elements found")

        # Save result
        pdf_document.save(output_path)
        pdf_document.close()

        print(f"\n{'=' * 60}")
        print("RESULT:")
        print(f"Links removed: {total_links_removed}")
        print(f"Images removed: {total_images_removed}")
        print(f"Cleaned file: {output_path}")

        return total_images_removed, total_links_removed

    def _has_target_link(self, obj_rect, page, target_domain):
        """Checks if an object has a link to the target domain"""
        for link in page.get_links():
            link_rect = fitz.Rect(link["from"])
            uri = link.get("uri", "").lower()
            if obj_rect.intersects(link_rect) and target_domain in uri:
                return True, link.get("uri", "")
        return False, ""

    def _remove_all_target_links(self, page, target_domain):
        """Removes all links to the target domain"""
        removed_count = 0
        links = page.get_links()

        for link in reversed(links):
            uri = link.get("uri", "").lower()
            if target_domain in uri:
                page.delete_link(link)
                removed_count += 1
                print(f"    ✓ Link removed: {link.get('uri', '')}")

        return removed_count

    def _remove_corner_images_with_links(
        self, page, target_domain, corner_threshold=0.7
    ):
        """Removes images in the bottom right corner with target links"""
        page_rect = page.rect
        right_threshold = page_rect.width * corner_threshold
        bottom_threshold = page_rect.height * corner_threshold

        print(f"    Page size: {page_rect.width:.0f}x{page_rect.height:.0f}")
        print(
            f"    Right edge threshold: {right_threshold:.0f}, bottom edge threshold: {bottom_threshold:.0f}"
        )

        removed_count = 0
        image_list = page.get_images(full=True)
        target_images = []
        images_to_remove = set()

        print(f"    Total images on page: {len(image_list)}")

        # Find all images in corner with target links
        for img in image_list:
            xref = img[0]
            img_rects = page.get_image_rects(xref)

            for img_rect in img_rects:
                print(
                    f"    Image xref:{xref} position: ({img_rect.x0:.0f}, {img_rect.y0:.0f}) size: {img_rect.width:.0f}x{img_rect.height:.0f}"
                )

                is_in_corner = (
                    img_rect.x0 >= right_threshold and img_rect.y0 >= bottom_threshold
                )
                print(
                    f"      In corner: {is_in_corner} (x0={img_rect.x0:.0f}>={right_threshold:.0f}, y0={img_rect.y0:.0f}>={bottom_threshold:.0f})"
                )

                if is_in_corner:
                    has_link, url = self._has_target_link(img_rect, page, target_domain)
                    print(f"      Has target link: {has_link} ({url})")
                    if has_link:
                        target_images.append((xref, img_rect, url))
                        images_to_remove.add(xref)

        # If we found images with target links in corner - remove ALL images in that corner
        if target_images:
            print(f"    Found {len(target_images)} images with target links in corner")

            # Collect all images in corner (even without links)
            for img in image_list:
                xref = img[0]
                img_rects = page.get_image_rects(xref)

                for img_rect in img_rects:
                    is_in_corner = (
                        img_rect.x0 >= right_threshold
                        and img_rect.y0 >= bottom_threshold
                    )
                    if is_in_corner:
                        images_to_remove.add(xref)
                        print(f"      Added for removal image xref:{xref} (in corner)")

            print(f"    Total to remove: {len(images_to_remove)} images")

            # Remove images
            for xref in images_to_remove:
                try:
                    # Get sizes to determine type
                    img_rects = page.get_image_rects(xref)
                    img_type = (
                        "logo" if any(r.height < 50 for r in img_rects) else "element"
                    )
                    sizes = [f"{r.width:.0f}x{r.height:.0f}" for r in img_rects]

                    page.delete_image(xref)
                    removed_count += 1
                    print(
                        f"    ✓ Removed image ({img_type}) xref:{xref}: {', '.join(sizes)}"
                    )
                except Exception as e:
                    print(f"    ✗ Error removing image xref:{xref}: {e}")
        else:
            print("    No images with target links found in corner")

        return removed_count

    def remove_watermarks(
        self,
        pdf_path,
        images_to_remove_info,
        output_pdf_path="output_without_watermarks.pdf",
    ):
        """Compatibility with old API - uses new algorithm"""
        try:
            images_removed, links_removed = self.clean_pdf_from_target_domain(
                pdf_path, output_pdf_path
            )

            print(f"\nNew PDF without watermarks saved as: {output_pdf_path}")
            print(f"Total elements removed: {images_removed + links_removed}")
            return output_pdf_path, None

        except Exception as e:
            return None, f"Error removing watermarks and saving PDF: {str(e)}"
