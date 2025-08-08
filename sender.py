"""
sender.py
---------
Sends WhatsApp phishing campaign messages via Selenium automation.
One-time QR login per session (Chrome profile). Sends messages to 200–1000 users in one run.
"""

import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from selenium.webdriver.chrome.options import Options

from db_utils import fetch_all_users, fetch_all_campaigns
from encrypt_utils import generate_encrypted_token


load_dotenv()
BASE_URL = os.getenv("AWARENESS_BASE_URL", "http://localhost:5000/redirect")

def setup_driver(profile_dir="WPSProfile"):
    """
    Sets up and returns a Selenium Chrome WebDriver using a persistent profile.
    Ensures QR scan is only required once per user.
    """
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={os.path.abspath(profile_dir)}")  # Persistent profile
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--lang=en")
    chrome_options.add_experimental_option("detach", True)  # Keeps the browser open after script ends
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://web.whatsapp.com/")
    print("[INFO] Please scan the QR code in Chrome window (if prompted) and wait for WhatsApp Web to load.")
    # Wait for user to scan QR code (if not already scanned)
    while True:
        try:
            driver.find_element(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']")
            print("[WAIT] Waiting for QR scan...")
            time.sleep(2)
        except NoSuchElementException:
            break  # QR gone, we're logged in
        except Exception:
            break
    print("[INFO] WhatsApp Web is ready!")
    return driver

from selenium.webdriver.common.keys import Keys

def send_message(driver, phone: str, message: str, max_retries=3):
    """
    Sends a WhatsApp message to the given phone number using Selenium.
    Returns True if successful, False otherwise.
    """
    import urllib.parse
    url = f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
    for attempt in range(max_retries):
        try:
            driver.get(url)
            time.sleep(4)  # Let the page load

            # Try to click 'Continue to Chat' (old WhatsApp Web) or 'Continue to Chat' (new WhatsApp)
            try:
                driver.find_element(By.XPATH, "//a[contains(@href, 'web.whatsapp.com/send')]").click()
                time.sleep(4)
            except NoSuchElementException:
                pass  # Already redirected

            # Try to find the chat input box in several possible ways
            input_box = None
            for _ in range(10):
                try:
                    # Try the most common input box selector
                    input_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")
                    break
                except NoSuchElementException:
                    # Try a more general fallback selector
                    try:
                        input_box = driver.find_element(By.XPATH, "//div[@contenteditable='true']")
                        break
                    except NoSuchElementException:
                        time.sleep(1)

            if not input_box:
                print(f"[ERROR] Input box not found for {phone}. Skipping.")
                return False

            input_box.click()  # Focus
            time.sleep(0.5)
            input_box.send_keys(Keys.ENTER)
            print(f"[OK] Message sent to {phone}")
            time.sleep(1.5)  # To avoid spamming/rate limits
            return True

        except WebDriverException as e:
            print(f"[ERROR] WebDriver error for {phone}: {e}. Retrying...")
            time.sleep(2)
    print(f"[FAIL] Could not send message to {phone}")
    return False


def run_whatsapp_campaign(campaign_id: int, country_code="90"):
    """
    Sends the selected campaign to all active users via WhatsApp Web using Selenium.
    """
    users = fetch_all_users(active_only=True)
    campaigns = fetch_all_campaigns()
    campaign = next((c for c in campaigns if c["campaign_id"] == campaign_id), None)
    if not campaign:
        print(f"[ERROR] Campaign ID {campaign_id} not found.")
        return

    message_template = campaign["message"]
    driver = setup_driver()

    for i, user in enumerate(users, start=1):
        # International format (ensure +90xxx, or just 90xxx if WhatsApp supports)
        phone = user['phone']
        if not phone.startswith("+") and not phone.startswith(country_code):
            phone = f"{country_code}{phone.lstrip('0')}"  # E.g. 532xxxxxx → 90532xxxxxx

        token = generate_encrypted_token(user['user_id'], campaign_id)
        phishing_url = f"{BASE_URL}?data={token}"

        # Build full message
        message = f"{message_template}\n{phishing_url}"
        print(f"[{i}/{len(users)}] Sending to {phone}...")
        success = send_message(driver, phone, message) 
        time.sleep(2)

    # The following block is commented out and not used:
    # # URL-encode message for WhatsApp
    # import urllib.parse
    # message_encoded = urllib.parse.quote(message)
    # print(f"[{i}/{len(users)}] Sending to {phone}...")
    # success = send_message(driver, phone, message_encoded)
    # # Wait a bit to avoid spam detection
    # time.sleep(2)

    print("[DONE] All messages have been sent (or attempted).")
    # Optionally: driver.quit()

if __name__ == "__main__":
    # Example: send campaign with ID 1
    run_whatsapp_campaign(1)
