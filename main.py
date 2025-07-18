import csv
import requests
import xml.etree.ElementTree as ET


PRODUCT_XML_PATH = "products.xml"
SITEMAP_URL = "https://jollein.com/sitemap_products_1.xml?from=8549537382598&to=8554444423366"
OUTPUT_CSV = "sku_ean_image_links.csv"


def load_products(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    products = {}
    for pm in root.findall(".//ProductXmlModel"):
        sku = pm.findtext("SKU")
        ean = pm.findtext("EAN")
        if sku and ean:
            products[sku] = ean
    return products


def parse_sitemap_images(sitemap_url):
    """
    Returns a list of (product_page_url, image_url) from the sitemap
    """
    r = requests.get(sitemap_url)
    r.raise_for_status()
    ns = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "image": "http://www.google.com/schemas/sitemap-image/1.1"
    }
    tree = ET.fromstring(r.text)
    url_entries = tree.findall(".//sm:url", ns)

    results = []
    for url in url_entries:
        loc = url.find("sm:loc", ns)
        product_url = loc.text if loc is not None else None

        images = url.findall("image:image/image:loc", ns)
        image_urls = [img.text for img in images if img.text]

        for img_url in image_urls:
            results.append((product_url, img_url))
    return results


def match_images_to_products(products, sitemap_images):
    """
    Returns list of (SKU, EAN, ImageURL)
    """
    rows = []

    for sku, ean in products.items():
        for product_url, img_url in sitemap_images:
            if sku in img_url or ean in img_url or (product_url and (sku in product_url or ean in product_url)):
                print(f"✅ Found match: SKU: {sku}, EAN: {ean}, IMAGE: {img_url}")
                rows.append((sku, ean, img_url))

    return rows


def write_csv(rows, csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "EAN", "ImageURL"])
        for row in rows:
            writer.writerow(row)
    print(f"✅ Written {csv_path}")


if __name__ == "__main__":
    print("Loading products…")
    products = load_products(PRODUCT_XML_PATH)

    print("Parsing sitemap with image URLs…")
    sitemap_images = parse_sitemap_images(SITEMAP_URL)

    print("Matching images to SKU/EAN…")
    rows = match_images_to_products(products, sitemap_images)

    print("Writing CSV…")
    write_csv(rows, OUTPUT_CSV)
