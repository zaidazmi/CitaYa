import logging
import os
import platform
import shutil
import subprocess
import time

from patchright.sync_api import sync_playwright

from .models import CustomerProfile

CDP_PORT = 9222
PAGE_TIMEOUT = 30000

_CHROME_PATHS = {
    "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "Linux": "/usr/bin/google-chrome",
    "Windows": None,
}

_chrome_process = None
_playwright_instance = None


def _find_chrome() -> str:
    system = platform.system()
    candidate = _CHROME_PATHS.get(system)
    if candidate and os.path.isfile(candidate):
        return candidate
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    if system == "Windows":
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")):
            path = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(path):
                return path
    raise FileNotFoundError(
        "Chrome not found. Install Google Chrome or set chrome_path in CustomerProfile."
    )


def launch_browser(context: CustomerProfile):
    global _chrome_process, _playwright_instance

    try:
        subprocess.run(["pkill", "-f", f"--remote-debugging-port={CDP_PORT}"],
                       capture_output=True, timeout=5)
        time.sleep(1)
    except Exception:
        pass

    user_data_dir = os.path.join(os.path.expanduser("~"), ".chrome-citaya")
    os.makedirs(user_data_dir, exist_ok=True)

    chrome_bin = context.chrome_path or _find_chrome()
    chrome_args = [
        chrome_bin,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ]

    if context.start_minimized:
        chrome_args.append("--start-minimized")

    _chrome_process = subprocess.Popen(
        chrome_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logging.info(f"Chrome launched (PID {_chrome_process.pid}, CDP port {CDP_PORT})")

    _playwright_instance = sync_playwright().start()

    cdp_url = f"http://127.0.0.1:{CDP_PORT}"
    for attempt in range(10):
        try:
            time.sleep(2)
            browser = _playwright_instance.chromium.connect_over_cdp(cdp_url)
            logging.info("Playwright connected to Chrome via CDP")
            return browser
        except Exception as e:
            if attempt < 9:
                logging.info(f"CDP not ready yet (attempt {attempt + 1}/10), retrying...")
            else:
                raise RuntimeError(f"Could not connect to Chrome CDP at {cdp_url}: {e}")


def close_browser(browser):
    global _chrome_process, _playwright_instance

    try:
        if browser:
            browser.close()
    except Exception:
        pass

    try:
        if _playwright_instance:
            _playwright_instance.stop()
            _playwright_instance = None
    except Exception:
        pass

    try:
        if _chrome_process:
            _chrome_process.terminate()
            _chrome_process.wait(timeout=5)
            _chrome_process = None
    except Exception:
        try:
            if _chrome_process:
                _chrome_process.kill()
                _chrome_process = None
        except Exception:
            pass

    try:
        subprocess.run(["pkill", "-f", f"--remote-debugging-port={CDP_PORT}"],
                       capture_output=True, timeout=5)
    except Exception:
        pass


def get_page_text(page) -> str:
    try:
        page.wait_for_selector("body", timeout=PAGE_TIMEOUT)
        return page.text_content("body") or ""
    except Exception:
        return ""


def close_cookie_banner(page):
    try:
        page.evaluate("""
            var banner = document.getElementById('cookie-law-info-bar');
            if (banner) banner.style.display = 'none';
            var accept = document.getElementById('cookie_action_close_header');
            if (accept) accept.click();
        """)
    except Exception:
        pass
