import random
import time
from playwright.sync_api import sync_playwright
from stealth_scrapers.stealth_utils import apply_stealth, block_heavy_resources
from stealth_scrapers.scraper_shared import get_proxy_config, get_database_session, save_to_db, USER_AGENTS

def run_yahoo():
    session = get_database_session()
    proxy_config = get_proxy_config()
    start_time = time.time()
    
    try:
        with sync_playwright() as p:
            print(f"[Yahoo] 🚀 Launching Browser for Yahoo Finance...")
            browser = p.chromium.launch(headless=False, proxy=proxy_config)
            
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={"Referer": "https://www.google.com/"},
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            # 1. Apply Stealth & RESOURCE BLOCKING
            apply_stealth(page)
            block_heavy_resources(page)

            url = "https://finance.yahoo.com/topic/stock-market-news/"
            print(f"[Yahoo] 🌐 Navigating to: {url}")

            try:
                # Reduced timeout to 45s (previously 90s)
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                time.sleep(random.uniform(2, 4))

                # 📜 SCROLL LOGIC: Yahoo needs scrolling to load the feed
                print("[Yahoo]    ⬇️ Scrolling to load feed...")
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1.5) # Reduced sleep slightly

                # --- ⚡ SUPER FAST BATCH EXTRACTION ---
                print("[Yahoo]    ⚡ Bulk extracting links via JS...")
                
                # Wait for at least some links to be present
                try:
                    page.wait_for_selector("li.js-stream-content a", timeout=5000)
                except:
                    pass

                articles_data = page.evaluate("""() => {
                    // Yahoo often uses 'li.js-stream-content' or similar for feed items
                    // We stick to a generic anchor search but filtered
                    const anchors = Array.from(document.querySelectorAll('a'));
                    const results = [];
                    const seen = new Set();
                    
                    for (const a of anchors) {
                        const title = a.innerText.trim();
                        let url = a.getAttribute('href');
                        
                        if (!url || !title) continue;
                        if (url.startsWith('/')) url = 'https://finance.yahoo.com' + url;
                        
                        // Filter logic in JS
                        if (!url.includes('/news/') && !url.includes('/m/') && !url.includes('finance.yahoo.com/news')) continue;
                        if (seen.has(url)) continue;
                        if (title.length < 25) continue;
                        if (title.includes('Stock Market News')) continue;
                        
                        seen.add(url);
                        results.push({title, url});
                        if (results.length >= 15) break; 
                    }
                    return results;
                }""")

                print(f"[Yahoo]    Found {len(articles_data)} valid articles via JS.")

                count = 0
                for article in articles_data:
                    try:
                        save_to_db(session, article['title'], article['url'], "Yahoo Finance", "Summary unavailable")
                        count += 1
                        if count >= 10: break
                    except:
                        continue

                print(f"[Yahoo] 🏁 Yahoo Scrape Complete. Saved {count} articles.")

            except Exception as e:
                print(f"[Yahoo] ❌ Yahoo Error: {e}")

            finally:
                browser.close()
                session.close()
    except Exception as e:
        print(f"[Yahoo] ❌ Browser launch error: {e}")
    finally:
        elapsed_time = time.time() - start_time
        print(f"[Yahoo] ⏱️  Yahoo Scraper Execution Time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    run_yahoo()