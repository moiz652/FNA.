import os
import sys
import random
import time
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- 🔌 DATABASE CONNECTION ---
# Add parent directory to path so we can find 'news_scraper'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from news_scraper.news_scraper.models import NewsArticle, db_connect, create_table


# --- 🌐 PROXY CONFIGURATION ---
def get_proxy_config():
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


# --- 🕵️‍♂️ STEALTH CONFIGURATION ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]


def apply_stealth(page):
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


def save_to_db(session, title, url, source, body):
    try:
        exists = session.query(NewsArticle).filter_by(url=url).first()
        if exists: return

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
        print(f"   ✅ SAVED: {title[:40]}...")
    except Exception as e:
        session.rollback()


def run_reuters_scraper():
    engine = db_connect()
    create_table(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    proxy_config = get_proxy_config()

    with sync_playwright() as p:
        print(f"🚀 Launching Browser for Reuters (US IP)...")
        browser = p.chromium.launch(headless=False, proxy=proxy_config)

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            extra_http_headers={"Referer": "https://www.google.com/"},
            ignore_https_errors=True
        )
        page = context.new_page()
        apply_stealth(page)

        url = "https://www.reuters.com/business"
        print(f"🌐 Navigating to: {url}")

        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            time.sleep(random.uniform(5, 8))

            print("👀 Looking for Reuters articles...")

            # Greedy Selector for Reuters
            all_links = page.locator("a[data-testid='Heading'], a[href*='/business/'], h3 a").all()
            print(f"   Found {len(all_links)} potential links. Filtering...")

            count = 0
            processed_urls = set()

            for link_el in all_links:
                try:
                    raw_text = link_el.inner_text().strip()
                    url = link_el.get_attribute("href")

                    if not url: continue
                    if url.startswith("/"):
                        url = "https://www.reuters.com" + url

                    if url in processed_urls: continue

                    # Smart Filters
                    if len(raw_text) < 20: continue
                    if len(raw_text.split()) < 4: continue

                    processed_urls.add(url)
                    save_to_db(session, raw_text, url, "Reuters", "Summary unavailable (Paywall)")
                    count += 1
                    if count >= 10: break

                except Exception as e:
                    continue

            print(f"🏁 Scrape Complete. Saved {count} articles.")

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            browser.close()
            session.close()


if __name__ == "__main__":
    run_reuters_scraper()