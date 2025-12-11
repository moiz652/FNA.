import random
import time
from playwright.sync_api import sync_playwright
from stealth_scrapers.stealth_utils import apply_stealth
# [NEW] Import shared logic
from stealth_scrapers.scraper_shared import get_proxy_config, get_database_session, save_to_db, USER_AGENTS

def run_reuters_scraper():
    session = get_database_session()
    proxy_config = get_proxy_config()
    start_time = time.time()
    
    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        print(f"[Reuters] 🚀 Launching Browser for Reuters (Attempt {attempt + 1}/{max_retries})...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, proxy=proxy_config)
                
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1280, "height": 720},
                    extra_http_headers={"Referer": "https://www.google.com/"},
                    ignore_https_errors=True
                )
                
                page = context.new_page()
                apply_stealth(page)

                url = "https://www.reuters.com/business/"
                print(f"[Reuters] 🌐 Navigating to: {url}")
                
                try:
                    page.goto(url, timeout=90000, wait_until="domcontentloaded")
                except:
                    print("[Reuters]    ⚠️ Timeout loading page, but continuing checks...")

                # Scroll to load dynamic content
                print("[Reuters]    ⬇️ Scrolling...")
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(random.uniform(2, 3))

                print("[Reuters] 👀 Looking for articles...")
                all_links = page.locator("a").all()
                print(f"[Reuters]    Found {len(all_links)} potential links. Filtering...")

                count = 0
                processed_urls = set()
                
                for link_el in all_links:
                    try:
                        url = link_el.get_attribute("href")
                        if not url: continue
                        
                        # Reuters Filter
                        if "/business/" not in url and "/markets/" not in url: continue
                        if url.startswith("/"): url = "https://www.reuters.com" + url
                        if url in processed_urls: continue

                        raw_text = link_el.inner_text().strip()
                        if not raw_text:
                            child = link_el.locator("h3, span").first
                            if child.count(): raw_text = child.inner_text().strip()

                        if len(raw_text) < 25: continue
                        
                        ban_words = ["Subscribe", "Register", "Sign In", "Reuters"]
                        if any(w in raw_text for w in ban_words): continue

                        processed_urls.add(url)
                        save_to_db(session, raw_text, url, "Reuters", "Summary unavailable")
                        count += 1
                        if count >= 10: break

                    except:
                        continue
                
                if count > 0:
                    elapsed_time = time.time() - start_time
                    print(f"[Reuters] 🏁 Scrape Complete. Saved {count} articles. (Time: {elapsed_time:.2f}s)")
                    return
                else:
                    print("[Reuters]    ⚠️ No valid articles passed filters.")
        
        except Exception as e:
            print(f"[Reuters] ❌ Error: {e}")
            time.sleep(5)

    session.close()
    elapsed_time = time.time() - start_time
    print(f"[Reuters] 🛑 Scrape Failed after {max_retries} attempts.")


if __name__ == "__main__":
    run_reuters_scraper()