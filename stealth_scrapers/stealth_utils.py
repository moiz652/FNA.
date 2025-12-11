from playwright.sync_api import Page, Route

def block_heavy_resources(page: Page):
    """
     intercepts and aborts requests for heavy resources (images, media, fonts) to speed up loading
    and reduce bandwidth/memory usage.
    """
    def handle_route(route: Route):
        if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
            try:
                route.abort()
            except:
                pass # Ignore errors if request is already handled/closed
        else:
            try:
                route.continue_()
            except:
                pass

    try:
        page.route("**/*", handle_route)
        print("[Stealth] 🛡️ Resource blocking enabled (Images, Fonts, Media, Stylesheets blocked).")
    except Exception as e:
        print(f"[Stealth] ⚠️ Failed to enable resource blocking: {e}")


def apply_stealth(page: Page):
    """
    Applies advanced stealth scripts to the page to evade bot detection.
    Includes WebDriver masking, plugin mocking, and permission mocking.
    """
    js_stealth = """
        // 1. Mask navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // 2. Mock navigator.plugins (Cheap mock)
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5] 
        });

        // 3. Mock navigator.permissions.query
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );

        // 4. Mock window.chrome (if needed)
        window.chrome = { runtime: {} };
        
        // 5. Randomize hardware concurrency slightly (optional)
        // Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
    """
    
    try:
        page.add_init_script(js_stealth)
        print("[Stealth] 🥷 Advanced stealth scripts injected (WebDriver, Plugins, Permissions).")
    except Exception as e:
        print(f"[Stealth] ❌ Failed to inject stealth scripts: {e}")
