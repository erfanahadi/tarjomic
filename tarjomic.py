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

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging to file and console
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

# SMS API info (adjust these with your actual API details)
SMS_API_URL = 'https://console.melipayamak.com/api/send/simple/31760f37050144939d098478f2127537'
SMS_FROM = '50002710011550'
SMS_TO = '09198115505'  # Change to your phone number

# Accounts list
accounts = [
    {"name": "erfan", "email": "erfan_ahadi2@ymail.com", "password": "123456"},
    {"name": "ashkan", "email": "e.ahadi4444@gmail.com", "password": "erfan4444"}
]

# Load existing orders from file or initialize empty dict
if os.path.exists('old_orders.json'):
    with open('old_orders.json', 'r', encoding='utf-8') as f:
        try:
            old_orders = json.load(f)
        except json.JSONDecodeError:
            old_orders = {}
else:
    old_orders = {}

# Chrome options for headless browsing
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # new headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def send_sms(text):
    data = {'from': SMS_FROM, 'to': SMS_TO, 'text': text}
    try:
        response = requests.post(SMS_API_URL, json=data)
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

def check_account(account):
    name = account['name']
    email = account['email']
    password = account['password']

    log_info(f"🔍 Checking [{name}]...")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://tarjomic.com/login")
        time.sleep(3)

        driver.find_element(By.ID, "txtEmailLogin").send_keys(email)
        driver.find_element(By.ID, "txtPasswordLogin").send_keys(password)

        login_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "btnLogin"))
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", login_button)
        time.sleep(5)

        
        if "login" in driver.current_url.lower():
            raise Exception("Login failed: Invalid credentials or page did not change.")

        driver.get("https://tarjomic.com/translator")
        time.sleep(3)

        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        session = requests.Session()
        for k, v in cookies.items():
            session.cookies.set(k, v)

        headers = {
            "Content-Type": "application/json",
            "Referer": "https://tarjomic.com/translator",
            "User-Agent": driver.execute_script("return navigator.userAgent")
        }
        payload = {"type": "WaitingForCurrentTranslator"}

        response = session.post("https://tarjomic.com/api/getOrders", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

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
    # Save old_orders to file
    with open('old_orders.json', 'w', encoding='utf-8') as f:
        json.dump(old_orders, f, ensure_ascii=False, indent=2)
    log_info("✅ Done\n")

if __name__ == "__main__":
    import os

    if os.environ.get('PYTEST_RUNNING') != 'true':
        main()
