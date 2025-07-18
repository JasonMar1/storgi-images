import csv
import os
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

PRODUCT_XML_PATH = "products.xml"
OUTPUT_CSV = "sku_ean_github_links.csv"
DOWNLOAD_FOLDER = "images"
CREDENTIALS_FILE = "client_secret_590736682375-g449nlvol2lg427bbo681n9fmo6vntf7.apps.googleusercontent.com.json"

# Your GitHub username and repo for generating the links later
GITHUB_USERNAME = "JasonMar1"
GITHUB_REPO = "storgi-images"

# Folder IDs from your links
FOLDER_IDS = [
    "1mkRGwSpQ68AoMRE3WxLkKmS_PRd_jzGD",
    "1y9ULh-7rULTajijsYdM8GXjYf__z6_br",
    "1TwwkhW8oowbyDWWTDqgFbTZChMp7GUvs",
    "1FhCAyLIZXXeGwHZtZGh8UkKRECMQXZS5",
    "1dLPlHFxtXaHABGtb5hFC1PZ1T9DpyuNI"
]

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def authenticate_google_drive():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8080)
    service = build('drive', 'v3', credentials=creds)
    return service


def list_files_in_folders(service, folder_ids):
    files = []
    for folder_id in folder_ids:
        query = f"'{folder_id}' in parents and mimeType contains 'image/'"
        page_token = None
        while True:
            response = service.files().list(q=query,
                                            spaces='drive',
                                            fields='nextPageToken, files(id, name, webContentLink)',
                                            pageToken=page_token).execute()
            for file in response.get('files', []):
                files.append({
                    'name': file.get('name'),
                    'link': f"https://drive.google.com/uc?export=download&id={file.get('id')}"
                })
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    return files


def load_products(xml_path):
    import xml.etree.ElementTree as ET
    tree = ET.parse(xml_path)
    root = tree.getroot()
    products = {}
    for pm in root.findall(".//ProductXmlModel"):
        sku = pm.findtext("SKU")
        ean = pm.findtext("EAN")
        if sku and ean:
            products[sku] = ean
    return products


def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as out_file:
            out_file.write(response.content)
        print(f"✅ Downloaded: {save_path}")
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")


def match_and_download_images(products, drive_files):
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    rows = []

    saved_skus = set()  # ✅ Keep track of SKUs already saved

    for sku, ean in products.items():
        for file in drive_files:
            name = file["name"]
            link = file["link"]

            if sku in name or ean in name:
                if sku in saved_skus:
                    break  # ✅ Skip further matches for this SKU
                saved_skus.add(sku)

                filename = f"{sku}.jpg"
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)

                # Download and save the file
                download_image(link, filepath)

                # Prepare GitHub raw link for this file
                github_link = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/refs/heads/main/{filename}"
                print(f"✅ Matched: SKU: {sku}, EAN: {ean}, GITHUB LINK: {github_link}")

                rows.append((sku, ean, github_link))
                break  # ✅ Stop checking other images after the first match for this SKU

    return rows


def write_csv(rows, csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "EAN", "GitHubLink"])
        for row in rows:
            writer.writerow(row)
    print(f"✅ Written {csv_path}")


if __name__ == "__main__":
    print("Authenticating Google Drive...")
    service = authenticate_google_drive()

    print("Listing files from folders...")
    drive_files = list_files_in_folders(service, FOLDER_IDS)

    print(f"Found {len(drive_files)} image files in Google Drive folders.")

    print("Loading products...")
    products = load_products(PRODUCT_XML_PATH)

    print("Matching & downloading images...")
    rows = match_and_download_images(products, drive_files)

    print("Writing CSV with GitHub links...")
    write_csv(rows, OUTPUT_CSV)
