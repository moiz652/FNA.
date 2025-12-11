import os
import sys
import time
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Fix for Windows Unicode handling
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

# --- 🔌 DATABASE CONNECTION ---
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from news_scraper.news_scraper.models import NewsArticle, db_connect, create_table
except ImportError:
    # Fallback if running from a different directory context
    try:
        sys.path.append(os.path.join(os.getcwd(), 'news_scraper'))
        from news_scraper.news_scraper.models import NewsArticle, db_connect, create_table
    except ImportError:
        print("❌ Error: Could not import database models. Check python path.")
        sys.exit(1)

# --- CONSTANTS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

# --- FUNCTIONS ---
def get_proxy_config():
    """Returns the Bright Data proxy configuration dictionary."""
    host = os.getenv("BRIGHTDATA_HOST")
    port = os.getenv("BRIGHTDATA_PORT")
    username = os.getenv("BRIGHTDATA_USERNAME")
    password = os.getenv("BRIGHTDATA_PASSWORD")

    if username and password:
        if "-country" not in username:
            username = f"{username}-country-us"
        return {
            "server": f"http://{host}:{port}",
            "username": username,
            "password": password,
        }
    return None

def get_database_session():
    """Initializes DB connection and returns a session."""
    engine = db_connect()
    create_table(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def save_to_db(session, title, url, source, body):
    """Saves a news article to the database, skipping duplicates."""
    try:
        exists = session.query(NewsArticle).filter_by(url=url).first()
        if exists:
            # print(f"   ⚠️ Duplicate: {title[:30]}...")
            return

        new_article = NewsArticle(
            source_site=source,
            url=url,
            title=title,
            body=body,
            pub_date=datetime.now(),
            crawl_datetime=datetime.now()
        )
        session.add(new_article)
        session.commit()
        print(f"   ✅ SAVED [{source}]: {title[:40]}...")
    except Exception as e:
        session.rollback()
        # print(f"   ❌ DB Error: {e}")
