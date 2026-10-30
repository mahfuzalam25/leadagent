import os
import sys
import csv
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_db, insert_lead

# ── CONFIG ──────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OUTPUT_DIR          = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
# ────────────────────────────────────────────────────────

def scrape_google_maps(query: str, location: str, max_results: int = 30) -> list:
    """
    Fetch businesses from Google Maps using the Places API (New).
    """
    search_term = f"{query} in {location}"
    results     = []
    seen_ids    = set()

    print(f"[+] Searching: {search_term}")

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.primaryType,places.businessStatus"
    }

    page_token = ""

    while len(results) < max_results:
        data = {
            "textQuery": search_term,
            "pageSize": 20  # Google API max page size
        }
        if page_token:
            data["pageToken"] = page_token

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                print(f"  [!] API Error: {response.text}")
                break

            json_data = response.json()
            places = json_data.get("places", [])

            if not places:
                break

            for place in places:
                if len(results) >= max_results:
                    break

                place_id = place.get("id")
                if place_id in seen_ids:
                    continue
                seen_ids.add(place_id)

                # Skip permanently closed businesses
                if place.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue

                name         = place.get("displayName", {}).get("text", "N/A")
                address      = place.get("formattedAddress", "N/A")
                phone        = place.get("nationalPhoneNumber", "N/A")
                website      = place.get("websiteUri", "N/A")
                rating       = str(place.get("rating", "N/A"))
                reviews      = str(place.get("userRatingCount", "N/A"))
                primary_type = place.get("primaryType", "")
                category     = primary_type.replace("_", " ").title() if primary_type else "N/A"

                business = {
                    "name":       name,
                    "category":   category,
                    "address":    address,
                    "phone":      phone,
                    "website":    website,
                    "rating":     rating,
                    "reviews":    reviews,
                    "location":   location,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }

                results.append(business)
                print(f"  [{len(results)}] {name} | {rating} stars | {address[:50]}")

            page_token = json_data.get("nextPageToken")
            if not page_token:
                break

            # Required delay before using the next page token
            time.sleep(2)

        except Exception as e:
            print(f"[!] Request error: {e}")
            break

    print(f"[+] Found {len(results)} businesses")
    return results

def save_to_csv(data: list, query: str, location: str) -> str:
    """Save scraped results to a timestamped CSV file."""
    if not data:
        print("[!] No data to save.")
        return ""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = os.path.join(
        OUTPUT_DIR,
        f"{query.replace(' ', '_')}_{location.replace(', ', '_')}_{timestamp}.csv"
    )

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print(f"\n[✓] Saved {len(data)} businesses to: {filename}")
    return filename

if __name__ == "__main__":
    init_db()
    data = scrape_google_maps("restaurants", "Dhaka, Bangladesh", 10)
    save_to_csv(data, "restaurants", "Dhaka, Bangladesh")

    inserted = 0
    skipped  = 0
    for business in data:
        if insert_lead(business):
            inserted += 1
        else:
            skipped += 1
    print(f"[✓] DB: {inserted} inserted, {skipped} skipped")