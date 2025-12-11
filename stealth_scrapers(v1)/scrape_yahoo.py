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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from news_scraper.news_scraper.models import NewsArticle, db_connect, create_table


# --- 🌐 PROXY & STEALTH SETUP ---
def get_proxy_config():
    host = os.getenv("BRIGHTDATA_HOST")
    port = os.getenv("BRIGHTDATA_PORT")
    username = os.getenv("BRIGHTDATA_USERNAME")
    password = os.getenv("BRIGHTDATA_PASSWORD")
    if username and password:
        if "-country" not in username: username = f"{username}-country-us"
        return {"server": f"http://{host}:{port}", "username": username, "password": password}
    return None


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]


def save_to_db(session, title, url, source, body):
    try:
        exists = session.query(NewsArticle).filter_by(url=url).first()
        if exists: return
        new_article = NewsArticle(
            source_site=source, url=url, title=title, body=body,
            pub_date=datetime.now(), crawl_datetime=datetime.now()
        )
        session.add(new_article)
        session.commit()
        print(f"   ✅ SAVED: {title[:40]}...")
    except Exception:
        session.rollback()


def run_yahoo():
    engine = db_connect()
    create_table(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    with sync_playwright() as p:
        print(f"🚀 Launching Browser for Yahoo Finance...")
        browser = p.chromium.launch(headless=False, proxy=get_proxy_config())
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            extra_http_headers={"Referer": "https://www.google.com/"},
            ignore_https_errors=True
        )
        page = context.new_page()

        url = "https://finance.yahoo.com/topic/stock-market-news/"
        print(f"🌐 Navigating to: {url}")

        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 5))

            # 📜 SCROLL LOGIC: Yahoo needs scrolling to load the feed
            print("   ⬇️ Scrolling to load feed...")
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(2)

            print("👀 Scanning Yahoo headlines...")

            # --- ⚡ GREEDY SELECTOR ---
            # Grab ALL links on the page
            links = page.locator("a").all()
            print(f"   Found {len(links)} raw links. Filtering...")

            count = 0
            processed_urls = set()

            for link in links:
                try:
                    # 1. Extract
                    title = link.inner_text().strip()
                    url = link.get_attribute("href")

                    if not url or not title: continue
                    if url.startswith("/"): url = "https://finance.yahoo.com" + url

                    # 2. Filter: Must look like a news URL
                    # Yahoo news URLs typically contain /news/ or /m/ or /video/
                    if "/news/" not in url and "/m/" not in url and "finance.yahoo.com/news" not in url:
                        continue

                    # Deduplicate
                    if url in processed_urls: continue

                    # 3. Quality Filter (Remove garbage)
                    if len(title) < 25: continue
                    if "Stock Market News" in title: continue

                    processed_urls.add(url)

                    # Save
                    save_to_db(session, title, url, "Yahoo Finance", "Summary unavailable")
                    count += 1
                    if count >= 10: break

                except:
                    continue

            print(f"🏁 Yahoo Scrape Complete. Saved {count} articles.")

        except Exception as e:
            print(f"❌ Yahoo Error: {e}")

        finally:
            browser.close()
            session.close()


if __name__ == "__main__":
    run_yahoo()