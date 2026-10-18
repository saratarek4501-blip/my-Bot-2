import asyncio, random, string
from playwright.async_api import async_playwright

TARGET_URLS = [
    "https://matrixzone-v2.netlify.app/",
    "https://matrixzone-hub.pages.dev/",
]

PROXIES = [
    "http://hdvnc9rccm:0fm2h5qecc@Lite.flashproxy.io:6969"
]

ANDROID_CHROME_UAS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
]

TOTAL_BATCHES = 9999999
BATCH_SIZE = 50  # (غيرها لـ 60 لما تبقى جاهز للتشغيل الكبير)
SESSION_TIMEOUT = 18

success_count = 0
fail_count = 0
counter_lock = asyncio.Lock()

async def main_page_optimize(route):
    try:
        rtype = route.request.resource_type
        url = route.request.url
        if rtype in ["document", "script"]:
            return await route.continue_()
        if rtype in ["xhr", "fetch"]:
            if "matrixzone" in url or "show.js" in url or "p.npcad.com" in url:
                return await route.continue_()
        return await route.abort()
    except Exception:
        try: await route.abort()
        except: pass

async def popup_strict_optimize(route):
    try:
        rtype = route.request.resource_type
        if rtype == "document":
            return await route.continue_()
        return await route.abort()
    except Exception:
        try: await route.abort()
        except: pass

async def run_session(browser, session_id, url, proxy):
    global success_count, fail_count
    context = None
    fail_reason = "Unknown"
    try:
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
        await page.route("**/*", main_page_optimize)

        popup_detected = asyncio.Event()

        def handle_popup(popup):
            async def monitor_popup():
                try:
                    await popup.route("**/*", popup_strict_optimize)
                    await popup.wait_for_load_state("domcontentloaded", timeout=6000)
                    await asyncio.sleep(random.uniform(3.0, 4.0))
                    popup_detected.set()
                except Exception:
                    pass
            asyncio.create_task(monitor_popup())

        context.on("page", handle_popup)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=8000)
        except Exception as e:
            fail_reason = "PageLoadError"
            raise e

        await asyncio.sleep(1.5)

        try:
            await page.mouse.wheel(0, random.randint(200, 400))
            await asyncio.sleep(0.8)
        except Exception:
            pass

        try:
            safe_spots = [(100, 300), (300, 500), (200, 700), (150, 450)]
            for _ in range(2):
                click_x, click_y = random.choice(safe_spots)
                await page.mouse.click(click_x, click_y)
                await asyncio.sleep(0.4)
        except Exception:
            pass

        try:
            await asyncio.wait_for(popup_detected.wait(), timeout=7.0)
            ad_shown = True
        except asyncio.TimeoutError:
            fail_reason = "PopupTimeout (No Ad Filled)"
            ad_shown = False

        if ad_shown:
            async with counter_lock:
                success_count += 1
                print(f"[Session {session_id}] SUCCESS | OK: {success_count} | FAIL: {fail_count}")
            return True
        else:
            async with counter_lock:
                fail_count += 1
                print(f"[Session {session_id}] FAILED [{fail_reason}] | OK: {success_count} | FAIL: {fail_count}")
            return False

    except Exception as e:
        if fail_reason == "Unknown":
            fail_reason = type(e).__name__
        async with counter_lock:
            fail_count += 1
            print(f"[Session {session_id}] FAILED [{fail_reason}] | OK: {success_count} | FAIL: {fail_count}")
        return False
    finally:
        if context:
            try: await context.close()
            except: pass

async def main():
    global success_count, fail_count
    session_id = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-popup-blocking",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--ignore-certificate-errors",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )
        for batch in range(TOTAL_BATCHES):
            tasks = [
                asyncio.wait_for(
                    run_session(browser, session_id := session_id + 1, random.choice(TARGET_URLS), random.choice(PROXIES)),
                    timeout=SESSION_TIMEOUT
                )
                for _ in range(BATCH_SIZE)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            print(f"--- Batch {batch + 1}/{TOTAL_BATCHES} Complete ---")
        await browser.close()

asyncio.run(main())
