import requests 
import os 
from dotenv import load_dotenv
import datetime 

load_dotenv()

SHEETY_TOKEN = os.environ.get("SHEETY_TOKEN")
# Support either variable name (your .env uses SHEETY_ENDPOINT_PRICE_HISTORY).
SHEET_ENDPOINT_PRICE_HISTORY = (
    os.environ.get("SHEET_ENDPOINT_PRICE_HISTORY")
    or os.environ.get("SHEETY_ENDPOINT_PRICE_HISTORY")
)
SHEETY_ENDPOINT_USERS = os.environ.get("SHEETY_ENDPOINT_USERS")

class DataManager:
    
    def __init__(self): 
        if not SHEETY_ENDPOINT_USERS:
            raise EnvironmentError("Missing required .env variable: SHEETY_ENDPOINT_USERS")
        if not SHEETY_TOKEN:
            raise EnvironmentError("Missing required .env variable: SHEETY_TOKEN")

        self.users_endpoint = SHEETY_ENDPOINT_USERS
        self.price_history_endpoint = SHEET_ENDPOINT_PRICE_HISTORY

        auth_value = self._normalize_auth_header(SHEETY_TOKEN)
        self.headers = {
            "Content-Type":  "application/json",
            "Authorization": auth_value,
        }

    @staticmethod
    def _normalize_auth_header(token: str) -> str:
        """
        Accepts common user-provided formats and returns the value that should be
        used for the HTTP Authorization header.

        Supported inputs:
        - raw token: "abc123"               -> "Bearer abc123"
        - bearer token: "Bearer abc123"     -> "Bearer abc123"
        - full header: "Authorization: Bearer abc123" -> "Bearer abc123"
        - basic auth: "Basic base64(...)"   -> "Basic base64(...)"
        """
        t = (token or "").strip()
        if not t:
            return ""

        # If user pasted "Authorization: Bearer xxx", strip the "Authorization:" prefix.
        if t.lower().startswith("authorization:"):
            t = t.split(":", 1)[1].strip()

        if t.lower().startswith("bearer "):
            return "Bearer " + t.split(None, 1)[1].strip()
        if t.lower().startswith("basic "):
            return "Basic " + t.split(None, 1)[1].strip()

        # Default to bearer if they provided just the token.
        return f"Bearer {t}"


    def retrieve_users(self) -> list[dict]:
        """
        Returns all rows from the 'users' sheet.
        Each row: { "id": int, "firstName": str, "lastName": str, "email": str }
        """
        try:
            response = requests.get(self.users_endpoint, headers=self.headers, timeout=20)
        except requests.RequestException as e:
            print(f"[ERROR] retrieve_users network error: {e}")
            return []

        if response.status_code != 200:
            print(f"[ERROR] retrieve_users failed ({response.status_code}): {response.text}")
            return []

        users = response.json().get("users", [])
        print(f"[INFO] Retrieved {len(users)} user(s).")
        return users

    # Backward-compatible misspelling (older callers).
    def retreive_users(self) -> list[dict]:
        return self.retrieve_users()

    def add_user(self, first_name: str, last_name: str, email: str) -> dict | None:
        """
        Adds a new row to the 'users' sheet.
        Guards against duplicate emails before inserting.
        Returns the created row on success, None if duplicate or on error.
        """
        email_norm = (email or "").strip().lower()
        if not email_norm:
            raise ValueError("Email is required.")

        # Duplicate guard
        for user in self.retrieve_users():
            existing = (user.get("email") or "").strip().lower()
            if existing and existing == email_norm:
                print(f"[INFO] {email_norm} is already registered.")
                return None

        payload = {
            "user": {
                "firstName": first_name,
                "lastName":  last_name,
                "email":     email_norm,
            }
        }

        try:
            response = requests.post(
                self.users_endpoint, json=payload, headers=self.headers, timeout=20
            )
        except requests.RequestException as e:
            print(f"[ERROR] add_user network error: {e}")
            return None

        if response.status_code not in (200, 201):
            if response.status_code in (401, 403):
                print(
                    "[ERROR] add_user unauthorized. Check SHEETY_TOKEN format; "
                    "it should be the raw token or start with 'Bearer '."
                )
            print(f"[ERROR] add_user failed ({response.status_code}): {response.text}")
            return None

        created = response.json().get("user", {})
        print(f"[SUCCESS] Added {first_name} {last_name} ({email_norm}).")
        return created

    def get_all_emails(self) -> list[str]:
        return [
            (u.get("email") or "").strip()
            for u in self.retrieve_users()
            if (u.get("email") or "").strip()
        ]

    def log_price_history(self, deals: list[dict]) -> None:
        """
        Writes one row per deal into the 'priceHistory' sheet.

        Sheet columns: week | destination | price
        Each row payload:
            { "priceHistory": { "week": "2025-W12", "destination": "LHR", "price": 520 } }
        """
        week_label = datetime.date.today().strftime("%Y-W%W")

        if not self.price_history_endpoint:
            raise EnvironmentError(
                "Missing required .env variable for price history logging: "
                "SHEET_ENDPOINT_PRICE_HISTORY (or SHEETY_ENDPOINT_PRICE_HISTORY)"
            )

        logged = 0
        skipped = 0

        for deal in deals:
            destination = deal.get("destination")
            price = deal.get("found_price")

            if not destination or price is None:
                skipped += 1
                continue

            payload = {
                "priceHistory": {
                    "week": week_label,
                    "destination": destination,
                    "price": price,
                }
            }

            response = requests.post(
                self.price_history_endpoint, json=payload, headers=self.headers
            )

            if response.status_code in (200, 201):
                logged += 1
            else:
                print(
                    f"[ERROR] Failed to log {destination} "
                    f"({response.status_code}): {response.text}"
                )
                skipped += 1

        print(f"[INFO] Price history logged: {logged} row(s), {skipped} skipped.")

    def retrieve_price_history(self) -> list[dict]:
        """
        Returns all rows from the 'priceHistory' sheet.
        Each row: { "id": int, "week": str, "destination": str, "price": float }
        """
        if not self.price_history_endpoint:
            raise EnvironmentError(
                "Missing required .env variable for price history retrieval: "
                "SHEET_ENDPOINT_PRICE_HISTORY (or SHEETY_ENDPOINT_PRICE_HISTORY)"
            )

        response = requests.get(self.price_history_endpoint, headers=self.headers)

        if response.status_code != 200:
            print(
                f"[ERROR] retrieve_price_history failed "
                f"({response.status_code}): {response.text}"
            )
            return []

        rows = response.json().get("priceHistory", [])
        print(f"[INFO] Retrieved {len(rows)} price history row(s).")
        return rows
