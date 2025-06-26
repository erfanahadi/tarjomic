#!/usr/bin/env python3

import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import logging
from datetime import datetime
import smtplib
import functools

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    filename='tarjomic_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def log_info(msg):
    print(msg)
    logging.info(msg)

def log_error(msg):
    print(msg)
    logging.error(msg)

# Retry decorator
def retry(max_attempts=3, delay=5):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    log_error(f"Retry {attempts}/{max_attempts} after error: {e}")
                    time.sleep(delay)
            raise Exception(f"{func.__name__} failed after {max_attempts} attempts.")
        return wrapper
    return decorator_retry

# SMS API
SMS_API_URL = 'https://console.melipayamak.com/api/send/simple/31760f37050144939d098478f2127537'
SMS_FROM = '50002710011550'
SMS_TO = '09198115505'

accounts = [
    {"name": "erfan", "email": "erfan_ahadi2@ymail.com", "password": "123456"},
    {"name": "ashkan", "email": "e.ahadi4444@gmail.com", "password": "erfan4444"}
]

# Load or initialize orders
if os.path.exists('old_orders.json'):
    with open('old_orders.json', 'r', encoding='utf-8') as f:
        try:
            old_orders = json.load(f)
        except json.JSONDecodeError:
            old_orders = {}
else:
    old_orders = {}

# Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def send_sms(text):
    data = {'from': SMS_FROM, 'to': SMS_TO, 'text': text}
    try:
        response = requests.post(SMS_API_URL, json=data, timeout=10)
        if response.ok:
            log_info(f"SMS sent successfully: {text}")
        else:
            log_error(f"Failed to send SMS: {response.status_code} {response.text}")
    except Exception as e:
        log_error(f"Exception sending SMS: {e}")

def send_email(receiver, subject, body):
    sender_email = 'e.ahadi4444@gmail.com'
    sender_password = 'bkztjgwxggmgibmc'
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(sender_email, receiver, message)
        log_info(f"Email sent successfully to {receiver}")
    except Exception as e:
        log_error(f"Failed to send email to {receiver}: {e}")
    finally:
        server.quit()

@retry(max_attempts=3, delay=8)
def perform_login(driver, email, password):
    driver.get("https://tarjomic.com/login")

    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "txtEmailLogin")))
    driver.find_element(By.ID, "txtEmailLogin").send_keys(email)
    driver.find_element(By.ID, "txtPasswordLogin").send_keys(password)

    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "btnLogin"))
    )
    driver.execute_script("arguments[0].click();", login_button)

    WebDriverWait(driver, 20).until(lambda d: "login" not in d.current_url.lower())

@retry(max_attempts=3, delay=5)
def get_orders(session, headers):
    payload = {"type": "WaitingForCurrentTranslator"}
    response = session.post("https://tarjomic.com/api/getOrders", json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def check_account(account):
    name = account['name']
    email = account['email']
    password = account['password']

    log_info(f"🔍 Checking [{name}]...")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        perform_login(driver, email, password)

        driver.get("https://tarjomic.com/translator")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        session = requests.Session()
        for k, v in cookies.items():
            session.cookies.set(k, v)

        headers = {
            "Content-Type": "application/json",
            "Referer": "https://tarjomic.com/translator",
            "User-Agent": driver.execute_script("return navigator.userAgent")
        }

        data = get_orders(session, headers)
        orders = data.get("orders", [])

        if not orders:
            log_info(f"ℹ️ No orders for [{name}]")
        else:
            log_info(f"ℹ️ Found {len(orders)} order(s) for [{name}]:")
            new_orders = []
            if name not in old_orders:
                old_orders[name] = []
            for order in orders:
                order_id = order.get('id')
                log_info(f" - Order ID: {order_id}")
                if order_id not in old_orders[name]:
                    old_orders[name].append(order_id)
                    new_orders.append(order_id)
            if new_orders:
                msg = f"New orders for {name}!\nOrder IDs: {', '.join(map(str, new_orders))}"
                send_sms(msg)
                send_email('e.ahadi4444@gmail.com', f"New orders for {name}", msg)

    except Exception as e:
        log_error(f"❌ [{name}] Error: {e}")
    finally:
        if driver:
            driver.quit()

def main():
    log_info("🔄 Checking accounts...")
    for account in accounts:
        check_account(account)
    with open('old_orders.json', 'w', encoding='utf-8') as f:
        json.dump(old_orders, f, ensure_ascii=False, indent=2)
    log_info("✅ Done\n")

if __name__ == "__main__":
    if os.environ.get('PYTEST_RUNNING') != 'true':
        main()
