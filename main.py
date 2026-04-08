import os
import sys
import argparse
from urllib.parse import urlparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, ProxySettings
from playwright_recaptcha import recaptchav2

# Load environment variables from a .env file if it exists
load_dotenv()


def confirm_host(host_id, proxy_url=None):
    target_url = f"https://www.noip.com/confirm-host?n={host_id}"
    
    # Parse the proxy URL into Playwright's required dictionary format
    proxy_settings: ProxySettings | None = None
    
    if proxy_url:
        parsed_proxy = urlparse(proxy_url)
        proxy_settings = {
            "server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"
        }
        if parsed_proxy.username:
            proxy_settings["username"] = parsed_proxy.username
        if parsed_proxy.password:
            proxy_settings["password"] = parsed_proxy.password
        print(f"Using Proxy: {proxy_settings['server']}")

    with sync_playwright() as p:
        # Launch Chromium with the proxy settings (if any are provided)
        browser = p.chromium.launch(headless=True, proxy=proxy_settings)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print(f"Navigating to {target_url} (Initial Load)")
            page.goto(target_url, wait_until="networkidle")

            # --- BYPASS UPSELL LOGIC ---
            print("Allowing No-IP to register session state...")
            page.wait_for_timeout(2000)

            print("Reloading to bypass the upsell page...")
            page.reload(wait_until="networkidle")
            # ---------------------------

            print("Waiting for reCAPTCHA and attempting to solve...")
            with recaptchav2.SyncSolver(page) as solver:
                solver.solve_recaptcha(wait=True)

            print("reCAPTCHA solved successfully.")

            # Find the button by its exact text
            submit_button = page.locator('button:has-text("Confirm your hostname now")')

            # Click the button
            print("Submitting the form...")
            submit_button.click()

            # Look for the success header that appears on the next page
            success_message = page.locator('h1:has-text("Update Successful")')

            try:
                # Wait up to 15 seconds for the success message to appear
                success_message.wait_for(state="visible", timeout=15000)
                print("Success! Host confirmed.")
                sys.exit(0)
            except Exception:
                print("Failed to confirm host or timed out waiting for success page.")
                sys.exit(1)

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-renew No-IP DDNS hostname.")
    parser.add_argument(
        "host_id",
        nargs="?",
        help="The No-IP confirmation host ID (the 'n' parameter in the URL).",
    )
    parser.add_argument(
        "--proxy_url",
        help="Proxy URL in the format http://USERNAME:PASSWORD@HOST:PORT/",
    )
    args = parser.parse_args()

    # Fall back to environment variables if no command-line argument is provided
    host_id = args.host_id or os.environ.get("NOIP_HOST_ID")
    proxy_url = args.proxy_url or os.environ.get("PROXY_URL")

    if not host_id:
        print(
            "Error: You must provide a host ID either as a command-line argument or via the NOIP_HOST_ID environment variable."
        )
        sys.exit(1)

    confirm_host(host_id, proxy_url)
