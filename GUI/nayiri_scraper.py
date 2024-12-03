import os
import time
import random
import requests
from tkinter import Tk, Label, Entry, Button, IntVar, BooleanVar, Checkbutton, filedialog, StringVar, ttk, PhotoImage
from tkinter import scrolledtext
from bs4 import BeautifulSoup
from PIL import Image
from fpdf import FPDF
import sys

BASE_URL = "http://nayiri.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.89 Safari/537.36"
}
def resource_path(relative_path):
    try:
            # PyInstaller creates a temp folder and stores files there
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
    
class RedirectText(object):
    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        self.widget.config(state='normal')
        self.widget.insert('end', string)
        self.widget.see('end')  # Auto-scroll to the bottom
        self.widget.config(state='disabled')

    def flush(self):
        pass

class NayiriScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nayiri Scraper")
        self.root.iconbitmap(resource_path("icon.ico"))
        self.start_icon = PhotoImage(file=resource_path("start_icon.png"))
        self.stop_icon = PhotoImage(file=resource_path("cancel_icon.png"))
        # Frame for Inputs
        input_frame = ttk.Frame(root, padding="10")
        input_frame.grid(row=0, column=0, sticky="ew")

        Label(input_frame, text="Dictionary ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.dictionary_id = StringVar()
        Entry(input_frame, textvariable=self.dictionary_id).grid(row=0, column=1, padx=5, pady=5)

        Label(input_frame, text="Start Page:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.start_page = IntVar(value=1)
        Entry(input_frame, textvariable=self.start_page).grid(row=1, column=1, padx=5, pady=5)

        Label(input_frame, text="End Page:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.end_page = IntVar(value=10)
        Entry(input_frame, textvariable=self.end_page).grid(row=2, column=1, padx=5, pady=5)

        Label(input_frame, text="Save Directory:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.save_dir = StringVar(value=os.getcwd())
        Entry(input_frame, textvariable=self.save_dir, state="readonly", width=40).grid(row=3, column=1, padx=5, pady=5)
        Button(input_frame, text="Browse", command=self.browse_directory).grid(row=3, column=2, padx=5, pady=5)

        # Options
        self.convert_to_pdf = BooleanVar(value=True)
        Checkbutton(input_frame, text="Convert to PDF", variable=self.convert_to_pdf).grid(row=4, column=0, sticky="w", padx=5, pady=5)

        self.delete_images = BooleanVar(value=False)
        Checkbutton(input_frame, text="Delete Images After PDF", variable=self.delete_images).grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Frame for buttons
        button_frame = ttk.Frame(root, padding="10")
        button_frame.grid(row=1, column=0, pady=10, sticky="n")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # Start Button
        self.start_button = Button(
            button_frame, image=self.start_icon, text="Start", command=self.start_scraping,
            compound="top", relief="flat"
        )
        self.start_button.grid(row=0, column=0, padx=20, pady=5)

        # Stop Button
        self.stop_button = Button(
            button_frame, image=self.stop_icon, text="Stop", command=self.stop_scraping,
            compound="top", relief="flat", state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=20, pady=5)

        # Center-align the button frame in the main window
        root.columnconfigure(0, weight=1)  # Ensure the main frame centers everything

        # Progress Bar and Status
        status_frame = ttk.Frame(root, padding="10")
        status_frame.grid(row=2, column=0, sticky="ew")

        self.status = StringVar(value="Ready")
        Label(status_frame, textvariable=self.status).pack(side="top", anchor="w", pady=5)

        self.progress = ttk.Progressbar(status_frame, length=400, mode="determinate")
        self.progress.pack(side="top", pady=5)

        # Log Area
        log_frame = ttk.LabelFrame(root, text="Log", padding="10")
        log_frame.grid(row=3, column=0, sticky="nsew")

        self.log_area = scrolledtext.ScrolledText(log_frame, width=60, height=15, state="disabled")
        self.log_area.pack(fill="both", expand=True)

        # Redirect stdout and stderr
        sys.stdout = RedirectText(self.log_area)
        sys.stderr = RedirectText(self.log_area)

        # Control flag
        self.stop_flag = False

    def log_message(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert('end', message + '\n')
        self.log_area.see('end')
        self.log_area.config(state='disabled')
        self.root.update()

    def browse_directory(self):
            selected_dir = filedialog.askdirectory(initialdir=self.save_dir.get())
            if selected_dir:
                self.save_dir.set(selected_dir)

    def fetch_image_url(self, session, page_number):
        url = f"{BASE_URL}/imagedDictionaryBrowser.jsp?dictionaryId={self.dictionary_id.get()}&pageNumber={page_number}"
        headers = HEADERS.copy()
        headers["Referer"] = url  # Set the referer header
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            self.log_message(f"Failed to fetch page {page_number}, status code: {response.status_code}")
            response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        img_tag = soup.find("img", id="pageImage")
        if img_tag and "src" in img_tag.attrs:
            img_src = img_tag["src"]
            if not img_src.startswith("http"):
                img_src = BASE_URL + img_src
            return img_src
        else:
            self.log_message(f"No image found on page {page_number}.")
        return None

    def download_image(self, session, image_url, output_path):
        headers = HEADERS.copy()
        headers["Referer"] = image_url  # Use image URL as referer
        response = session.get(image_url, headers=headers, stream=True)
        if response.status_code != 200:
            self.log_message(f"Failed to download image: {image_url}, status code: {response.status_code}")
            response.raise_for_status()
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        self.log_message(f"Image saved to {output_path}.")

    def scrape_dictionary(self):
        self.status.set("Scraping started...")
        self.stop_flag = False
        
        output_dir = self.save_dir.get()
        os.makedirs(output_dir, exist_ok=True)
        
        start_page = self.start_page.get()
        end_page = self.end_page.get()
        total_pages = end_page - start_page + 1
        self.progress["maximum"] = total_pages
        self.progress["value"] = 0  # Reset progress bar
        
        with requests.Session() as session:
            for page in range(start_page, end_page + 1):
                if self.stop_flag:
                    self.status.set("Scraping stopped.")
                    self.log_message("Scraping stopped by user.")
                    break
                try:
                    self.status.set(f"Fetching page {page}...")
                    self.log_message(f"Fetching page {page}...")
                    self.root.update()
                    image_url = self.fetch_image_url(session, page)
                    if image_url:
                        self.log_message(f"Image URL: {image_url}")
                        output_path = os.path.join(output_dir, f"page_{page:03}.jpg")
                        self.status.set(f"Downloading page {page}...")
                        self.log_message(f"Downloading image to {output_path}...")
                        self.download_image(session, image_url, output_path)
                        time.sleep(random.uniform(1, 3))
                    else:
                        self.status.set(f"Image not found for page {page}.")
                        self.log_message(f"No image found for page {page}.")
                except Exception as e:
                    error_message = f"Error on page {page}: {e}"
                    self.status.set(error_message)
                    self.log_message(error_message)
                finally:
                    self.progress["value"] += 1
                    self.root.update()
        
        if not self.stop_flag and self.convert_to_pdf.get():
            self.status.set("Converting images to PDF...")
            self.log_message("Converting images to PDF...")
            self.create_pdf(output_dir)
        
        if not self.stop_flag:
            self.status.set("Scraping completed!")
            self.log_message("Scraping completed!")
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"

    def create_pdf(self, output_dir):
        """
        Create a PDF from downloaded images in the specified output directory.
        """
        pdf = FPDF()
        image_files = sorted([f for f in os.listdir(output_dir) if f.endswith(".jpg")])

        if not image_files:
            self.status.set("No images found for PDF creation.")
            self.log_message("No images found for PDF creation.")
            return

        for file in image_files:
            try:
                image_path = os.path.join(output_dir, file)
                with Image.open(image_path) as img:
                    img = img.convert("RGB")
                    img_width, img_height = img.size
                    pdf_width = 190  # Max width for FPDF
                    aspect_ratio = img_width / img_height
                    pdf_height = pdf_width / aspect_ratio
                    if pdf_height > 277:
                        pdf_height = 277
                        pdf_width = pdf_height * aspect_ratio
                    pdf.add_page()
                    pdf.image(image_path, x=10, y=10, w=pdf_width, h=pdf_height)
            except Exception as e:
                error_message = f"Skipping invalid or corrupted image {file}: {e}"
                self.log_message(error_message)
                continue

        dictionary_id = self.dictionary_id.get()  # Use the user-provided dictionary ID
        pdf_output_path = os.path.join(output_dir, f"{dictionary_id}.pdf")
        if len(pdf.pages) > 0:
            pdf.output(pdf_output_path)
            self.status.set(f"PDF created successfully at {pdf_output_path}.")
            self.log_message(f"PDF created successfully at {pdf_output_path}.")
            if self.delete_images.get():
                for file in image_files:
                    os.remove(os.path.join(output_dir, file))
                    self.log_message(f"Deleted {file}")
        else:
            self.status.set("PDF creation failed: No valid images.")
            self.log_message("PDF creation failed: No valid images.")

    def start_scraping(self):
        self.start_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.progress["value"] = 0
        self.scrape_dictionary()

    def stop_scraping(self):
        self.stop_flag = True

if __name__ == "__main__":
    root = Tk()
    app = NayiriScraperApp(root)
    root.mainloop()
