import asyncio, random, string
from urllib.parse import urlparse
from playwright.async_api import async_playwright

TARGET_URLS = [
    "http://p.npcad.com/go/506538/758940",
    "http://p.npcad.com/go/506538/758938",
    "http://p.npcad.com/go/506538/758939"
]

# 👇 البروكسي بتاعك هنا
PROXIES = [
    "http://qrl3m07935:97e22fy0f8@lite.flashproxy.io:6969"
]

ANDROID_CHROME_UAS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
]

TOTAL_BATCHES = 9999999
BATCH_SIZE = 100 # جيت هاب يقدر يشيل ده بسهولة
SESSION_TIMEOUT = 15

success_count = 0
fail_count = 0
counter_lock = asyncio.Lock()

async def optimize(route):
    try:
        if route.request.resource_type in ["image", "media", "font", "stylesheet", "script", "ping", "eventsource", "xhr", "fetch", "other"]:
            return await route.abort()
        await route.continue_()
    except Exception:
        try: await route.abort()
        except: pass

async def run_session(browser, session_id, url, proxy):
    global success_count, fail_count
    context = None
    try:
        # إعدادات البروكسي مع إضافة جلسة عشوائية لتغيير الـ IP
        proto, rest = proxy.split("://", 1)
        creds, endpoint = rest.split("@", 1)
        salt = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        u, pw = creds.split(":", 1) if ":" in creds else (creds, "")
        
        proxy_config = {
            "server": f"{proto}://{endpoint}",
            "username": f"{u}-session-{salt}",
            "password": pw
        }

        context = await browser.new_context(
            user_agent=random.choice(ANDROID_CHROME_UAS),
            proxy=proxy_config,
            locale="en-US",
            viewport={"width": 412, "height": 915},
            is_mobile=True,
            has_touch=True
        )
        context.set_default_timeout(SESSION_TIMEOUT * 1000)
        page = await context.new_page()
        await page.route("**/*", optimize)
        
        first_domain = None
        second_domain_detected = asyncio.Event()

        def on_request(request):
            nonlocal first_domain
            try:
                domain = urlparse(request.url).netloc
                if not domain:
                    return
                if first_domain is None:
                    first_domain = domain
                    return
                if domain != first_domain:
                    second_domain_detected.set()
            except Exception:
                pass

        page.on("request", on_request)

        await page.goto(url, wait_until="commit", timeout=SESSION_TIMEOUT * 1000)
        
        try:
            await asyncio.wait_for(second_domain_detected.wait(), timeout=SESSION_TIMEOUT)
        except asyncio.TimeoutError:
            pass

        if second_domain_detected.is_set():
            async with counter_lock:
                success_count += 1
                print(f"[Session {session_id}] SUCCESS | OK: {success_count} | FAIL: {fail_count}", flush=True)
            return True
        else:
            async with counter_lock:
                fail_count += 1
                print(f"[Session {session_id}] FAILED (No 2nd Domain) | OK: {success_count} | FAIL: {fail_count}", flush=True)
            return False

    except Exception:
        async with counter_lock:
            fail_count += 1
            print(f"[Session {session_id}] FAILED | OK: {success_count} | FAIL: {fail_count}", flush=True)
        return False
    finally:
        if context:
            try: await context.close()
            except: pass

async def main():
    global success_count, fail_count
    session_id = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        for batch in range(TOTAL_BATCHES):
            tasks = [
                asyncio.wait_for(
                    run_session(browser, session_id := session_id + 1, random.choice(TARGET_URLS), random.choice(PROXIES)),
                    timeout=SESSION_TIMEOUT
                )
                for _ in range(BATCH_SIZE)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            print(f"--- Batch {batch + 1}/{TOTAL_BATCHES} Complete ---", flush=True)
        await browser.close()

asyncio.run(main())
