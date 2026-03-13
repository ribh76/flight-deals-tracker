from dotenv import load_dotenv
import requests 
import os 
import datetime 
import time 
import json 

load_dotenv() 
API_KEY = os.environ.get("SEARCH_API_KEY")

DEAL_THRESHOLDS = {
    "LHR": 650,   # London, England 
    "DXB": 850,   # Dubai, UAE
    "CDG": 650,   # Paris, France
    "FCO": 750,   # Rome, Italy
    "JFK": 300,   # New York City, USA (domestic baseline)
    "NRT": 900,   # Tokyo, Japan
   }

class FlightFinder: 
    def __init__(self, origin: str): 
        if not API_KEY:
            raise EnvironmentError("Missing required .env variable: SEARCH_API_KEY")
        self.API_KEY = API_KEY 
        self.origin = origin.upper().strip() 

    def _explore_price(self, iata_dest: str) -> float | None:
        """
        Uses engine=google_travel_explore — no specific dates required.
        Google picks the cheapest flexible dates automatically.
        """
        url = "https://www.searchapi.io/api/v1/search"
        params = {
            "engine": "google_travel_explore",
            "departure_id": self.origin,
            "arrival_id": iata_dest,
            "travel_mode": "flights_only",
            "currency": "USD",
            "api_key": self.API_KEY,
        }

        try:
            response = requests.get(url=url, params=params, timeout=15)
        except requests.RequestException as e:
            print(f"[ERROR] Network error (explore) for {iata_dest}: {e}")
            return None

        if response.status_code != 200:
            print(f"[ERROR] API {response.status_code} for {iata_dest}: {response.text[:200]}")
            return None

        data = response.json()
        destinations = data.get("destinations", [])

        if not destinations:
            print(
                f"[DEBUG] No destinations in explore response for {iata_dest}. "
                f"Keys: {list(data.keys())}"
            )
            return None

        prices: list[float] = []
        for dest in destinations:
            flight = dest.get("flight", {})
            p = flight.get("price")
            if p is not None:
                try:
                    prices.append(float(p))
                except (ValueError, TypeError):
                    pass

        if not prices:
            print(f"[DEBUG] No readable prices in explore response for {iata_dest}")
            return None

        return min(prices)

    def _flights_price(self, iata_dest: str) -> float | None:
        outbound = (datetime.date.today() + datetime.timedelta(weeks=4)).strftime("%Y-%m-%d")

        url = "https://www.searchapi.io/api/v1/search"
        params = {
            "engine": "google_flights",
            "departure_id": self.origin,
            "arrival_id": iata_dest,
            "flight_type": "one_way",
            "outbound_date": outbound,      # REQUIRED
            "currency": "USD",
            "sort_by": "price",
            "api_key": self.API_KEY,
        }

        try:
            response = requests.get(url=url, params=params, timeout=15)
        except requests.RequestException as e:
            print(f"[ERROR] Network error (flights) for {iata_dest}: {e}")
            return None

        if response.status_code != 200:
            print(f"[ERROR] API {response.status_code} for {iata_dest}: {response.text[:200]}")
            return None

        data = response.json()

        # price_insights.lowest_price is the most reliable single figure
        lowest = data.get("price_insights", {}).get("lowest_price")
        if lowest is not None:
            return float(lowest)

        # fall back: scan best_flights + other_flights top-level price field
        all_groups = data.get("best_flights", []) + data.get("other_flights", [])
        if not all_groups:
            print(f"[DEBUG] No flight groups for {iata_dest}. Keys: {list(data.keys())}")
            return None

        prices = []
        for group in all_groups:
            p = group.get("price")
            if p is not None:
                try:
                    prices.append(float(p))
                except (ValueError, TypeError):
                    pass

        if not prices:
            print(f"[DEBUG] No readable prices in flights response for {iata_dest}")
            return None

        return min(prices)

    def search_for_flight(self, iata_dest: str) -> float | None:
        """
        Main price lookup used by the weekly scan.

        Tries the date-specific Google Flights engine first (more consistent single-price fields),
        then falls back to the flexible Explore engine.
        """
        iata_dest = iata_dest.upper().strip()
        price = self._flights_price(iata_dest)
        if price is not None:
            return price
        return self._explore_price(iata_dest)

    @staticmethod
    def _is_good_deal(iata: str, price: float) -> bool:
        threshold = DEAL_THRESHOLDS.get(iata)

        if not threshold:
            return False
        return price <= threshold

    @staticmethod
    def _deal_score_from_threshold(threshold: float | None, price: float) -> float:
        if not threshold:
            return 0.0
        return round((threshold - price) / threshold, 2)

    @staticmethod
    def _export_to_json(deals: list[dict], filename: str = "general_deals.json") -> None:
        try:
            with open(filename, "w") as f:
                json.dump(deals, f, indent=4)
            print(f"[SUCCESS] Deals exported to {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to export JSON: {e}")

    def find_general_deals(self) -> list[dict]: 
        deals = []

        for iata_code, threshold in DEAL_THRESHOLDS.items(): 
            print(f"[INFO] Searching flights from {self.origin} to {iata_code}")
            price = self.search_for_flight(iata_code)

            if price is None: 
                print(f"[WARNING] No price found for {iata_code}" )
                continue 

            is_deal = self._is_good_deal(iata_code, price)
            deal_score = self._deal_score_from_threshold(threshold, price)

            result = {
                "origin": self.origin,
                "destination": iata_code,
                "threshold": threshold,
                "found_price": price,
                "is_deal": is_deal,
                "deal_score": deal_score,
                "timestamp": time.time()
            }

            deals.append(result)

            if is_deal:
                print(f"[DEAL FOUND] {iata_code} at ${price}")
            else:
                print(f"[INFO] No deal for {iata_code}. Price: ${price}")

            time.sleep(1)  # Prevent rate limiting

        self._export_to_json(deals)
        return deals
        

    def search_custom_destination(self, iata_dest: str, custom_threshold: float | None = None) -> dict | None:
            iata_dest = iata_dest.upper().strip()
            print(f"[INFO] Searching {self.origin} -> {iata_dest} ...")
            price = self._flights_price(iata_dest)

            if price is None:
                return None

            threshold = custom_threshold if custom_threshold is not None else DEAL_THRESHOLDS.get(iata_dest)
            is_deal   = (price <= threshold) if threshold else False
            score     = self._deal_score_from_threshold(threshold, price) if threshold else 0.0

            return {
                "origin":      self.origin,
                "destination": iata_dest,
                "threshold":   threshold,
                "found_price": price,
                "is_deal":     is_deal,
                "deal_score":  score,
                "timestamp":   time.time(),
            }

        
