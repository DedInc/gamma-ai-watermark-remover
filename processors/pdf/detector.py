import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class WatermarkDetector:
    def __init__(self, target_domain: str = "gamma.app") -> None:
        self.target_domain = target_domain

    def _has_target_link(
        self, obj_rect: fitz.Rect, page: fitz.Page, target_domain: str
    ) -> tuple[bool, str]:
        """Checks if an object has a link to the target domain"""
        for link in page.get_links():
            link_rect = fitz.Rect(link["from"])
            uri = link.get("uri", "").lower()
            if obj_rect.intersects(link_rect) and target_domain in uri:
                return True, link.get("uri", "")
        return False, ""

    def identify_watermarks(
        self, pdf_path: str
    ) -> tuple[list[dict[str, object]], str | None]:
        """Identifies elements to remove (watermarks from target domain)"""
        results = []
        try:
            pdf_document = fitz.open(pdf_path)
            logger.info(f"\nSearching for {self.target_domain} domain elements...\n")

            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                logger.info(f"Page {page_num + 1}:")

                # Check images in bottom right corner with target links
                page_rect = page.rect
                right_threshold = page_rect.width * 0.7
                bottom_threshold = page_rect.height * 0.7

                image_list = page.get_images(full=True)
                found_targets = False

                for img in image_list:
                    xref = img[0]
                    img_rects = page.get_image_rects(xref)

                    for img_rect in img_rects:
                        is_in_corner = (
                            img_rect.x0 >= right_threshold
                            and img_rect.y0 >= bottom_threshold
                        )
                        if is_in_corner:
                            has_link, url = self._has_target_link(
                                img_rect, page, self.target_domain
                            )
                            if has_link:
                                results.append(
                                    {
                                        "page": page_num,
                                        "type": "corner_image_with_link",
                                        "xref": xref,
                                        "url": url,
                                    }
                                )
                                found_targets = True
                                logger.info(f"  ✓ Found image with target link: {url}")

                # Check links to target domain
                links = page.get_links()
                for link in links:
                    uri = link.get("uri", "").lower()
                    if self.target_domain in uri:
                        results.append(
                            {
                                "page": page_num,
                                "type": "target_link",
                                "link": link,
                                "url": link.get("uri", ""),
                            }
                        )
                        found_targets = True
                        logger.info(f"  ✓ Found target link: {link.get('uri', '')}")

                if not found_targets:
                    logger.info("  No target elements found")

            pdf_document.close()

            if not results:
                logger.info(f"\n{self.target_domain} domain elements not found in PDF.")

            return results, None

        except Exception as e:
            return [], f"Error searching for elements: {str(e)}"
