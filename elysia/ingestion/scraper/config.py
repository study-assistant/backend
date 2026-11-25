from pathlib import Path

SCRAPER_VERSION = "0.1.0"

# scraper/
SCRAPER_DIR = Path(__file__).resolve().parent

LINKS_FILE = SCRAPER_DIR / "links.csv"