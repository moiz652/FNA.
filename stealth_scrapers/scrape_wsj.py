import random
import time
from playwright.sync_api import sync_playwright
from stealth_scrapers.stealth_utils import apply_stealth, block_heavy_resources
from stealth_scrapers.scraper_shared import get_proxy_config, get_database_session, save_to_db, USER_AGENTS

def run_wsj_scraper():
    session = get_database_session()
    proxy_config = get_proxy_config()
    start_time = time.time()

    # Reduced retries to fail fast
    max_retries = 2
    for attempt in range(max_retries):
        print(f"[WSJ] 🚀 Launching Browser for WSJ (Attempt {attempt + 1}/{max_retries})...")
        browser = None
        try:
            with sync_playwright() as p:
                # Launch options
                browser = p.chromium.launch(
                    headless=False, 
                    proxy=proxy_config,
                    args=["--disable-blink-features=AutomationControlled"] # Extra evasion
                )

                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1280, "height": 720},
                    extra_http_headers={"Referer": "https://www.google.com/"},
                    ignore_https_errors=True
                )
                
                page = context.new_page()
                
                # 1. Apply Stealth & Resource Blocking
                apply_stealth(page)
                block_heavy_resources(page)

                print("[WSJ]    Navigating to WSJ Homepage...")
                # Increased timeout to 60s, handle timeout gracefully
                try:
                    page.goto("https://www.wsj.com", timeout=60000, wait_until="domcontentloaded")
                except Exception as e:
                    print(f"[WSJ]    ⚠️ Goto timeout/error: {e}. Checking if page loaded anyway...")

                # 2. Anti-Bot / Verification Handling
                print("[WSJ]    🕵️ Checking for anti-bot verification...")
                # Human-like mouse jiggle to pass "Are you human?" checks
                # We do this regardless of goto success, as we might be on the verification screen
                for _ in range(5):
                    x, y = random.randint(100, 700), random.randint(100, 500)
                    page.mouse.move(x, y, steps=10)
                    time.sleep(0.5)

                # Wait for main content or verification resolution
                try:
                    # Wait for a common element like the logo, headline, OR the verification challenge
                    # If verification screen is present, we might need to wait longer
                    page.wait_for_selector("nav, h2, #captcha-container", timeout=15000)
                except:
                    print("[WSJ]    ⚠️ Timeout waiting for main content (possibly still verifying or blocked). Continuing...")

                # 3. Navigate to Tech
                print("[WSJ]    🖱️  Navigating to Tech section...")
                target_url = "https://www.wsj.com/tech"
                
                try:
                    # Try clicking if button exists (more human)
                    tech_btn = page.locator("a[href*='/tech']").first
                    if tech_btn.is_visible(timeout=3000):
                        tech_btn.click()
                        page.wait_for_url("**/tech**", timeout=30000, wait_until="domcontentloaded")
                    else:
                        raise Exception("Tech button not found")
                except:
                    # Fallback direct navigation
                    print("[WSJ]    -> Direct navigation to Tech...")
                    page.goto(target_url, timeout=45000, wait_until="domcontentloaded")

                print("[WSJ] 👀 Scanning for articles...")
                
                # Wait briefly for dynamic content
                time.sleep(random.uniform(2, 4))
                
                # Extract links
                all_links = page.locator("a[href*='/articles/'], a[href*='/tech/'], a[href*='/business/']").all()
                print(f"[WSJ]    Found {len(all_links)} potential links. Filtering...")
                
                if len(all_links) == 0:
                     print("[WSJ]    ❌ No links found! Possible block.")
                     # If blocked, maybe retry?
                     raise Exception("Block detected - No links found")

                count = 0
                processed_urls = set()
                
                for link_el in all_links:
                    try:
                        url = link_el.get_attribute("href")
                        if not url: continue
                        
                        if url.startswith("/"):
                            url = "https://www.wsj.com" + url

                        if url in processed_urls: continue

                        # Get Text
                        raw_text = link_el.inner_text().strip()
                        if not raw_text:
                             # Try finding a child header
                             heading = link_el.locator("h2, h3, h4").first
                             if heading.count(): 
                                 raw_text = heading.inner_text().strip()
                        
                        # Filters
                        if len(raw_text) < 15: continue
                        ban_words = ["Subscribe", "Sign In", "Cookie", "Policy", "Read More"]
                        if any(word in raw_text for word in ban_words): continue

                        # Save
                        processed_urls.add(url)
                        save_to_db(session, raw_text, url, "WSJ", "Summary unavailable (Paywall)")
                        count += 1
                        
                        if count >= 10: break

                    except Exception:
                        continue
                
                if count > 0:
                    elapsed_time = time.time() - start_time
                    print(f"[WSJ] 🏁 Scrape Complete. Saved {count} articles. (Time: {elapsed_time:.2f}s)")
                    return
                else:
                    print("[WSJ]    ⚠️ Links found but none passed filters.")
                    
        except Exception as e:
            print(f"[WSJ] ❌ Error: {e}")
            time.sleep(3)

    session.close()
    elapsed_time = time.time() - start_time
    print(f"[WSJ] 🛑 Scrape Failed after {max_retries} attempts. (Total Time: {elapsed_time:.2f}s)")

if __name__ == "__main__":
    run_wsj_scraper()