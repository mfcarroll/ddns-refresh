import os
import sys
import argparse
from playwright.sync_api import sync_playwright
from playwright_recaptcha import recaptchav2


def confirm_host(host_id):
    target_url = f"https://www.noip.com/confirm-host?n={host_id}"

    with sync_playwright() as p:
        # Launch Chromium in headless mode (Required for GitHub Actions)
        browser = p.chromium.launch(headless=True)
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
                sys.exit(0)  # Exit with success code
            except Exception:
                print("Failed to confirm host or timed out waiting for success page.")
                sys.exit(1)  # Exit with error code so GitHub knows it failed

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
    args = parser.parse_args()

    # Fall back to environment variable if no command-line argument is provided
    host_id = args.host_id or os.environ.get("NOIP_HOST_ID")

    if not host_id:
        print(
            "Error: You must provide a host ID either as a command-line argument or via the NOIP_HOST_ID environment variable."
        )
        sys.exit(1)

    confirm_host(host_id)
