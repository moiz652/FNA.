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
sys.path.append(os.getcwd())
#from news_scraper.models import NewsArticle, db_connect
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
        print(f"   ✅ SAVED: {title[:40]}...")
    except Exception as e:
        session.rollback()


def run_wsj_scraper():
    engine = db_connect()
    create_table(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    proxy_config = get_proxy_config()

    with sync_playwright() as p:
        print(f"🚀 Launching Browser for WSJ (US IP)...")

        browser = p.chromium.launch(headless=False, proxy=proxy_config)

        # 🧠 SMART CONTEXT: Add Google Referer
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            extra_http_headers={"Referer": "https://www.google.com/"},
            ignore_https_errors=True
        )
        page = context.new_page()
        apply_stealth(page)

        # 1. Go to HOME PAGE first (Builds trust)
        print("🌐 Navigating to WSJ Homepage...")
        try:
            page.goto("https://www.wsj.com", timeout=90000, wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 5))

            # 2. Human Navigation: Click 'Tech' or navigate explicitly
            print("[WSJ]    🖱️  Simulating human activity...")

            # Try to find the Tech link in navigation
            try:
                # Look for 'Tech' or 'Technology' in the nav bar
                tech_btn = page.locator("a[href*='/tech'], a[href*='/technology']").first
                if tech_btn.count() > 0 and tech_btn.is_visible():
                    tech_btn.click()
                    time.sleep(random.uniform(5, 8))  # Wait for load
                else:
                    # Fallback: Just navigate if button not found
                    print("   -> Menu link not found, manually navigating...")
                    page.goto("https://www.wsj.com/tech", timeout=90000, wait_until="domcontentloaded")
                    time.sleep(random.uniform(5, 8))
            except:
                # If click fails, force navigate
                page.goto("https://www.wsj.com/tech", timeout=90000, wait_until="domcontentloaded")
                time.sleep(random.uniform(5, 8))

            # Screenshot to verify we are actually on the news page now
            page.screenshot(path="debug_wsj_v2.png")

            print("👀 Looking for WSJ articles...")

            # --- ⚡ GREEDY SELECTOR (Same as Bloomberg) ---
            all_links = page.locator("a").all()
            print(f"[WSJ]    Found {len(all_links)} potential links. Filtering...")

            count = 0
            processed_urls = set()

            for link_el in all_links:
                try:
                    # 1. Extract Info
                    url = link_el.get_attribute("href")
                    if not url: continue

                    # WSJ Filter
                    if "/articles/" not in url and "/tech/" not in url and "/business/" not in url:
                        continue

                    if url.startswith("/"):
                        url = "https://www.wsj.com" + url

                    if url in processed_urls: continue

                    # 2. Get Headline
                    raw_text = link_el.inner_text().strip()

                    # Fallback: Check children if text is empty
                    if not raw_text:
                        child = link_el.locator("h2, h3, span").first
                        if child.count(): raw_text = child.inner_text().strip()

                    # 3. Quality Filter
                    if len(raw_text) < 20: continue
                    if len(raw_text.split()) < 4: continue

                    ban_words = ["Subscribe", "Sign In", "Cookie", "Policy", "Skip to", "Read More", "Listen", "Watch"]
                    if any(word in raw_text for word in ban_words): continue

                    # Save
                    processed_urls.add(url)
                    save_to_db(session, raw_text, url, "WSJ", "Summary unavailable (Paywall)")
                    count += 1

                    if count >= 10: break

                except Exception as e:
                    continue

            print(f"[WSJ] 🏁 Scrape Complete. Saved {count} articles.")

        except Exception as e:
            print(f"[WSJ] ❌ Error: {e}")

        finally:
            browser.close()
            session.close()


if __name__ == "__main__":
    run_wsj_scraper()