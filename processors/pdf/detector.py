import fitz  # PyMuPDF


def has_target_link(obj_rect, page, target_domain):
    """Checks if an object has a link to the target domain"""
    for link in page.get_links():
        link_rect = fitz.Rect(link["from"])
        uri = link.get("uri", "").lower()
        if obj_rect.intersects(link_rect) and target_domain in uri:
            return True, link.get("uri", "")
    return False, ""


def remove_all_target_links(page, target_domain):
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


def remove_corner_images_with_links(page, target_domain, corner_threshold=0.7):
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
                has_link, url = has_target_link(img_rect, page, target_domain)
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
                    img_rect.x0 >= right_threshold and img_rect.y0 >= bottom_threshold
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


class WatermarkDetector:
    def __init__(self, target_domain="gamma.app"):
        self.target_domain = target_domain

    def identify_watermarks(self, pdf_path):
        """Identifies elements to remove (watermarks from target domain)"""
        results = []
        try:
            pdf_document = fitz.open(pdf_path)
            print(f"\nSearching for {self.target_domain} domain elements...\n")

            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                print(f"Page {page_num + 1}:")

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
                            has_link, url = has_target_link(
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
                                print(f"  ✓ Found image with target link: {url}")

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
                        print(f"  ✓ Found target link: {link.get('uri', '')}")

                if not found_targets:
                    print("  No target elements found")

            pdf_document.close()

            if not results:
                print(f"\n{self.target_domain} domain elements not found in PDF.")

            return results, None

        except Exception as e:
            return [], f"Error searching for elements: {str(e)}"
