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


def run_bloomberg_scraper():
    engine = db_connect()
    create_table(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    proxy_config = get_proxy_config()

    with sync_playwright() as p:
        print(f"🚀 Launching Browser (Targeting US IPs)...")

        browser = p.chromium.launch(headless=False, proxy=proxy_config)

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            # 🧠 TRICK 1: Tell them we came from Google
            extra_http_headers={"Referer": "https://www.google.com/"},
            ignore_https_errors=True
        )
        page = context.new_page()
        apply_stealth(page)

        url = "https://www.bloomberg.com/technology"
        print(f"🌐 Navigating to: {url}")

        try:
            page.goto(url, timeout=120000, wait_until="domcontentloaded")

            # 🧠 TRICK 2: Human Mouse Movement
            print("   🖱️  Simulating human activity...")
            for _ in range(3):
                x, y = random.randint(100, 800), random.randint(100, 600)
                page.mouse.move(x, y)
                time.sleep(random.uniform(0.5, 1.5))
                page.mouse.wheel(0, random.randint(200, 500))

            time.sleep(random.uniform(3, 5))  # Let the page settle

            print("👀 Looking for articles...")

            # Greedy Selector + Smart Filter
            all_links = page.locator("a[href*='/news/articles/']").all()

            # --- 🛠️ DIAGNOSTIC DUMP ---
            if len(all_links) == 0:
                print("   ❌ No links found! Saving page source for debugging...")
                with open("bloomberg_error_dump.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                page.screenshot(path="debug_bloomberg_failed.png")
                print("   📸 Check 'debug_bloomberg_failed.png' and 'bloomberg_error_dump.html'")
            else:
                print(f"   Found {len(all_links)} raw links. Filtering for quality...")

            count = 0
            processed_urls = set()

            for link_el in all_links:
                try:
                    raw_text = link_el.inner_text().strip()
                    url = link_el.get_attribute("href")

                    if not url: continue
                    if url.startswith("/"):
                        url = "https://www.bloomberg.com" + url

                    if url in processed_urls: continue

                    # Quality Filters
                    if len(raw_text) < 25: continue
                    if len(raw_text.split()) < 4: continue

                    ban_words = ["Getty Images", "Bloomberg", "Photo", "Credit", "Courtesy"]
                    if any(word in raw_text for word in ban_words): continue

                    processed_urls.add(url)
                    save_to_db(session, raw_text, url, "Bloomberg", "Summary unavailable (Paywall)")
                    count += 1

                    if count >= 10: break

                except Exception as e:
                    continue

            print(f"🏁 Scrape Complete. Saved {count} high-quality articles.")

        except Exception as e:
            print(f"❌ Error: {e}")

        finally:
            browser.close()
            session.close()


if __name__ == "__main__":
    run_bloomberg_scraper()