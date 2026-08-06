from pathlib import Path

SCRAPER_VERSION = "0.1.0"

# scraper/
SCRAPER_DIR = Path(__file__).resolve().parent

# backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3] 

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
# PROCESSED_DATA_DIR = DATA_DIR / "processed"

# create folders automatically
DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)

LINKS_FILE = SCRAPER_DIR / "links.csv"