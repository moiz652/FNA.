import random
import time
from playwright.sync_api import sync_playwright
from stealth_scrapers.stealth_utils import apply_stealth
# [NEW] Import shared logic
from stealth_scrapers.scraper_shared import get_proxy_config, get_database_session, save_to_db, USER_AGENTS

def run_bloomberg_scraper():
    session = get_database_session()
    proxy_config = get_proxy_config()
    start_time = time.time()
    
    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        print(f"[Bloomberg] 🚀 Launching Browser for Bloomberg (Attempt {attempt + 1}/{max_retries})...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, proxy=proxy_config)
                
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport=None, # Allow maximize
                    extra_http_headers={"Referer": "https://www.google.com/"},
                    ignore_https_errors=True
                )
                
                page = context.new_page()
                apply_stealth(page)

                url = "https://www.bloomberg.com/markets"
                print(f"[Bloomberg] 🌐 Navigating to: {url}")
                
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                time.sleep(random.uniform(3, 5))

                print("[Bloomberg]    🖱️  Simulating human activity...")
                page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                
                # Check for "Verify you are human"
                if "captcha" in page.title().lower() or "robot" in page.content().lower():
                    print("[Bloomberg]    ⚠️ CAPTCHA detected. Waiting 10s for manual solve (if visible)...")
                    time.sleep(10)

                print("[Bloomberg] 👀 Looking for articles...")
                all_links = page.locator("a").all()
                print(f"[Bloomberg]    Found {len(all_links)} potential links. Filtering...")
                
                if len(all_links) == 0:
                     print("[Bloomberg]    ❌ No links found! Possible block.")
                     time.sleep(2)
                     continue # Retry

                count = 0
                processed_urls = set()
                
                for link_el in all_links:
                    try:
                        url = link_el.get_attribute("href")
                        if not url: continue
                        
                        if "/news/articles/" not in url: continue
                        if url.startswith("/"): url = "https://www.bloomberg.com" + url
                        if url in processed_urls: continue

                        raw_text = link_el.inner_text().strip()
                        if not raw_text:
                            child = link_el.locator("h3, span").first
                            if child.count(): raw_text = child.inner_text().strip()

                        if len(raw_text) < 20: continue
                        if len(raw_text.split()) < 4: continue
                        
                        ban_words = ["Subscribe", "Sign In", "Terms", "Privacy"]
                        if any(w in raw_text for w in ban_words): continue

                        processed_urls.add(url)
                        save_to_db(session, raw_text, url, "Bloomberg", "Summary unavailable")
                        count += 1
                        if count >= 10: break

                    except:
                        continue
                
                if count > 0:
                    elapsed_time = time.time() - start_time
                    print(f"[Bloomberg] 🏁 Scrape Complete. Saved {count} articles. (Time: {elapsed_time:.2f}s)")
                    return
                else:
                    print("[Bloomberg]    ⚠️ No valid articles passed filters.")
        
        except Exception as e:
            print(f"[Bloomberg] ❌ Error: {e}")
            time.sleep(5)

    session.close()
    elapsed_time = time.time() - start_time
    print(f"[Bloomberg] 🛑 Scrape Failed after {max_retries} attempts.")

if __name__ == "__main__":
    run_bloomberg_scraper()