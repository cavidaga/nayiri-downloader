import os
import time
import random
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

BASE_URL = "http://nayiri.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.89 Safari/537.36",
}


def fetch_image_url(session, dictionary_id, page_number):
    """
    Fetch the image URL for a specific page number.
    """
    referer_url = f"{BASE_URL}/imagedDictionaryBrowser.jsp?dictionaryId={dictionary_id}&pageNumber={page_number}"
    response = session.get(referer_url, headers={**HEADERS, "Referer": referer_url})
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    img_tag = soup.find("img", id="pageImage")
    if img_tag and "src" in img_tag.attrs:
        return BASE_URL + img_tag["src"]
    return None


def download_image(session, image_url, output_path, referer):
    """
    Download an image from the given URL to the specified output path.
    """
    response = session.get(image_url, headers={**HEADERS, "Referer": referer}, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as file:
        for chunk in response.iter_content(1024):
            file.write(chunk)


def scrape_dictionary(start_page, end_page, dictionary_id, output_dir):
    """
    Scrape the dictionary images and save them locally.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with requests.Session() as session:
        for page in range(start_page, end_page + 1):
            print(f"Fetching page {page}...")
            referer_url = f"{BASE_URL}/imagedDictionaryBrowser.jsp?dictionaryId={dictionary_id}&pageNumber={page}"
            try:
                image_url = fetch_image_url(session, dictionary_id, page)
                if image_url:
                    output_path = os.path.join(output_dir, f"page_{page:03}.jpg")
                    print(f"Downloading {image_url} to {output_path}...")
                    download_image(session, image_url, output_path, referer_url)
                    time.sleep(random.uniform(1, 10))  # Mimic human behaviour
                else:
                    print(f"Image not found for page {page}.")
            except requests.RequestException as e:
                print(f"Error fetching page {page}: {e}")


def convert_to_pdf(image_dir, pdf_path):
    """
    Convert a folder of images to a single PDF.
    """
    pdf = FPDF()
    images = sorted(
        [os.path.join(image_dir, img) for img in os.listdir(image_dir) if img.endswith(".jpg")]
    )

    if not images:
        print("No images found in directory for PDF conversion.")
        return

    for image in images:
        pdf.add_page()
        pdf.image(image, x=0, y=0, w=210, h=297)  # A4 size: 210x297 mm

    pdf.output(pdf_path, "F")
    print(f"PDF created successfully: {pdf_path}")


if __name__ == "__main__":
    print("Welcome to the Dictionary Scraper!")
    dictionary_id = int(input("Enter the dictionary ID: "))
    start_page = int(input("Enter the start page number: "))
    end_page = int(input("Enter the end page number: "))
    output_dir = f"dictionary_{dictionary_id}"
    pdf_output_path = f"dictionary_{dictionary_id}.pdf"

    # Scrape the dictionary images
    scrape_dictionary(start_page, end_page, dictionary_id, output_dir)

    # Convert images to PDF
    convert_to_pdf(output_dir, pdf_output_path)
