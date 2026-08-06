import requests
from pathlib import Path
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; scraping-bot/1.0)"
}

# Custom exception for fetcher failures.
class FetchError(Exception):
    pass

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS)
        # r = requests.get(url, headers=HEADERS, timeout=20) # TODO timeout for potentially slow pages that can freeze the whole run
        r.raise_for_status()
        r.encoding = "utf-8" # force UTF-8 decoding
        return BeautifulSoup(r.text, "lxml")
    except requests.RequestException as e:
        raise FetchError(f"Failed to fetch {url}: {e}") from e

# Download a file (PDF, image, etc.) to dest_path.
# Creates parent directories if needed.
def download_file(url: str, dest_path: Path) -> Path:
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, headers=HEADERS, stream=True)
        r.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path
    except requests.RequestException as e:
        raise FetchError(f"Failed to download {url}: {e}") from e
    except OSError as e:
        raise FetchError(f"Failed to write file {dest_path}: {e}") from e
