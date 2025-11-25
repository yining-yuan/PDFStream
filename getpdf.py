import os
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---- Config ----
CONTENTS_URL = "https://www.ifaamas.org/Proceedings/aamas2025/forms/contents.htm"

PDF_BASE_2025 = "https://www.ifaamas.org/Proceedings/aamas2025/pdfs/"
# Optional fallback: some PDFs currently live under 2024 directory
PDF_BASE_2024 = "https://www.ifaamas.org/Proceedings/aamas2024/pdfs/"

# Download folder: ~/Downloads/AAMAS2025
DOWNLOAD_DIR = Path.home() / "Downloads" / "AAMAS2025"


def get_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AAMAS-scraper/1.0)"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.text


def find_pdf_filenames(html: str) -> list[str]:
    """Return unique filenames like ['p1.pdf', 'p3.pdf', 'p14.pdf', ...]."""
    soup = BeautifulSoup(html, "html.parser")
    filenames = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # We only care about things like ../pdfs/p14.pdf, ../pdfs/p142.pdf, etc.
        if href.startswith("../pdfs/") and href.lower().endswith(".pdf"):
            filenames.add(href.split("/")[-1])

    return sorted(filenames, key=lambda s: int("".join(ch for ch in s if ch.isdigit()) or 0))


def download_pdf(filename: str, session: requests.Session) -> None:
    """Download a single PDF, trying 2025 first, then 2024 as fallback."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOAD_DIR / filename

    if dest.exists():
        print(f"[skip] {filename} already exists")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AAMAS-scraper/1.0)"
    }

    # Try 2025 path first
    url_2025 = urljoin(PDF_BASE_2025, filename)
    print(f"[try ] {filename} from 2025 …")
    r = session.get(url_2025, headers=headers, stream=True)

    if r.status_code == 404:
        # Fallback to 2024 path
        url_2024 = urljoin(PDF_BASE_2024, filename)
        print(f"       2025 returned 404, trying 2024 …")
        r = session.get(url_2024, headers=headers, stream=True)

    if r.status_code != 200:
        print(f"[fail] {filename} (HTTP {r.status_code})")
        return

    # Stream to disk
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"[done] {filename} -> {dest}")


def main():
    print(f"Fetching contents from {CONTENTS_URL} …")
    html = get_html(CONTENTS_URL)
    pdf_filenames = find_pdf_filenames(html)

    print(f"Found {len(pdf_filenames)} PDF links.")
    if not pdf_filenames:
        print("No PDF links found. Check the page or the parser.")
        return

    print(f"Downloading into: {DOWNLOAD_DIR}\n")

    with requests.Session() as session:
        for i, filename in enumerate(pdf_filenames, start=1):
            print(f"({i}/{len(pdf_filenames)})", end=" ")
            try:
                download_pdf(filename, session)
            except Exception as e:
                print(f"[error] {filename}: {e}")


if __name__ == "__main__":
    main()
