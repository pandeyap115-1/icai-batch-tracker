import os
import time
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

URL = "https://www.icaionlineregistration.org/LaunchBatchDetail.aspx"
REGION = "Western"
COURSE = "Advanced (ICITSS) MCS Course"

BRANCH_INTERVALS = {
    "MUMBAI": 20,
    "VASAI": 30,
    "THANE": 80
}

def get_due_branches():
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("[Manual Trigger] Checking ALL branches...")
        return list(BRANCH_INTERVALS.keys())

    epoch_min = int(time.time() // 60)
    due = []
    
    if (epoch_min // 10) % 2 == 0:
        due.append("MUMBAI")
    if (epoch_min // 10) % 3 == 0:
        due.append("VASAI")
    if (epoch_min // 10) % 8 == 0:
        due.append("THANE")
        
    return due if due else ["MUMBAI"]

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[-] Telegram failed: {e}")

def inspect_branch(page, target: str):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    dropdowns = page.locator("select")
    
    dropdowns.nth(0).select_option(label=REGION)
    page.wait_for_timeout(3000)
    
    dropdowns.nth(1).select_option(label=target)
    page.wait_for_timeout(3000)
    
    dropdowns.nth(2).select_option(label=COURSE)
    page.wait_for_timeout(3000)
    
    page.locator("input[value='Get List'], button:has-text('Get List')").first.click()
    page.wait_for_timeout(4000)
    
    rows = page.locator("table tr").all()
    open_batch_cards = []
    
    for row in rows[1:]:
        cols = [c.strip() for c in row.locator("td").all_inner_texts()]
        if len(cols) >= 5:
            try:
                seats = int(cols[1])
                if seats > 0:
                    batch_no = cols[0]
                    from_date = cols[2]
                    to_date = cols[3]
                    batch_time = cols[4]
                    card = (
                        f"🔹 *Batch:* `{batch_no}`\n"
                        f"🪑 *Seats Left:* *{seats}*\n"
                        f"📅 *Dates:* {from_date} to {to_date}\n"
                        f"⏰ *Timing:* {batch_time}\n"
                    )
                    open_batch_cards.append(card)
            except ValueError:
                continue
                
    if open_batch_cards:
        return "\n".join(open_batch_cards)
    return None

def main():
    due_targets = get_due_branches()
    print(f"Checking branches: {', '.join(due_targets)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
        page = context.new_page()

        for target in due_targets:
            try:
                batch_info = inspect_branch(page, target)
                if batch_info:
                    msg = (
                        f"🚨 *SEATS AVAILABLE - {target}!*\n\n"
                        f"{batch_info}\n"
                        f"🔗 [Direct Registration Link]({URL})"
                    )
                    send_telegram(msg)
                    print(f"[!] Active seats found for {target}!")
                else:
                    print(f"[-] {target}: No open seats.")
            except Exception as err:
                print(f"[-] Error checking {target}: {err}")

if __name__ == "__main__":
    main()
