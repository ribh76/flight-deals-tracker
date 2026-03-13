import requests 
import os 
import json 

from flight_finder import FlightFinder
from data_manager import DataManager
from notification_manager import NotificationManager


def load_deals(filename="general_deals.json"): 
        try: 
            with open(filename, "r") as file: 
                return json.load(file) 
        except FileNotFoundError: 
            print("[ERROR] Deals file not found.")
            return [] 
        
def run_weekly_scan(origin: str) -> list[dict]:
    """
    1. FlightFinder scans all 6 preset destinations and exports to general_deals.json
    2. main loads the JSON
    3. Passes the full list to NotificationManager.send_general_deals()
       (NM internally filters for is_deal=True before rendering)
    4. Returns the full deal list for the UI to display
    """
    print(f"\n=== Weekly Scan | Origin: {origin} ===")

    # Step 1 — search & export
    finder = FlightFinder(origin)
    deals  = finder.find_general_deals()       # also writes general_deals.json

    # Optionally reload from disk (keeps run_weekly_scan aligned with the exported artifact)
    deals = load_deals("general_deals.json") or deals

    if not deals:
        print("[WARNING] No deals data to send.")
        return []

    try:
        dm     = DataManager()
        emails = dm.get_all_emails()

        if emails:
            nm = NotificationManager()
            nm.send_general_deals(content=deals, recipient_emails=emails)
        else:
            print("[INFO] No Flight Club members yet — skipping email.")

    except Exception as e:
        print(f"[ERROR] Could not complete email step: {e}")

    return deals


def run_custom_search(origin: str, destination: str,
                      user_email: str,
                      custom_threshold: float | None = None) -> dict | None:
    """
    1. FlightFinder searches a specific user-supplied destination
    2. If a deal is found, NotificationManager.send_deals() alerts the user
    3. Returns the result dict (or None if no data)
    """
    print(f"\n=== Custom Search | {origin} -> {destination} ===")

    finder = FlightFinder(origin)
    result = finder.search_custom_destination(destination, custom_threshold)

    if result is None:
        print("[WARNING] No flight data returned for custom search.")
        return None

    if result.get("is_deal") and user_email:
        try:
            nm = NotificationManager()
            nm.send_deals(content=result, recipient_email=user_email)
        except Exception as e:
            print(f"[ERROR] Could not send deal alert: {e}")
    else:
        print(f"[INFO] No deal found for {destination} — no email sent.")

    return result


# ── Quick manual test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    # Change origin and email to test locally
    deals = run_weekly_scan(origin="LAX")
    print(f"\n{len(deals)} destination(s) scanned.")

    true_deals = [d for d in deals if d.get("is_deal")]
    print(f"{len(true_deals)} deal(s) found.")
