from flask import Flask, render_template, request, jsonify, Response
import json
import os
from datetime import datetime
import random
import csv
from io import StringIO

app = Flask(__name__)

# Configuration - set RENTCAST_API_KEY in environment for real API
RENTCAST_API_KEY = os.environ.get("RENTCAST_API_KEY", "")
USE_REAL_API = bool(RENTCAST_API_KEY)

# Expanded sample data for Castle Rock / Douglas County demo (updated with larger home comps)
SAMPLE_COMPS = [
    {"address": "467 Lorraway Drive, Castle Rock, CO 80108", "price": 1540000, "sqft": 5737, "beds": 4, "baths": 5, "sold": "2026-10-09", "pps": 268},
    {"address": "6568 Leilani Lane, Castle Rock, CO 80108", "price": 875000, "sqft": 4643, "beds": 4, "baths": 4, "sold": "2026-10-09", "pps": 188},
    {"address": "6014 Hoofbeat Place, Castle Rock, CO 80108", "price": 665000, "sqft": 4113, "beds": 4, "baths": 3, "sold": "2026-10-07", "pps": 162},
    {"address": "5302 Danvers Court, Castle Rock, CO 80104", "price": 747900, "sqft": 2520, "beds": 3, "baths": 3, "sold": "2026-10-07", "pps": 297},
    {"address": "4068 Silver Swan Place, Castle Rock, CO 80109", "price": 640000, "sqft": 2947, "beds": 5, "baths": 4, "sold": "2026-10-07", "pps": 217},
    {"address": "2450 Garganey Drive, Castle Rock, CO 80104", "price": 560000, "sqft": 3332, "beds": 4, "baths": 3, "sold": "2026-10-07", "pps": 168},
    {"address": "3531 Morning Glory Drive, Castle Rock, CO 80109", "price": 530000, "sqft": 2070, "beds": 3, "baths": 4, "sold": "2026-10-09", "pps": 256},
    {"address": "4350 Old Windmill Way, Castle Rock, CO 80109", "price": 590000, "sqft": 2552, "beds": 4, "baths": 3, "sold": "2026-10-09", "pps": 231},
    {"address": "1178 N Deckers Pl, Castle Rock, CO 80104", "price": 510000, "sqft": 1686, "beds": 3, "baths": 3, "sold": "2026-10-08", "pps": 303},
    {"address": "6052 Wescroft Avenue, Castle Rock, CO 80104", "price": 470000, "sqft": 1699, "beds": 3, "baths": 3, "sold": "2026-10-08", "pps": 277},
    {"address": "4219 Dunsinane Way, Castle Rock, CO 80104", "price": 646000, "sqft": 4009, "beds": 4, "baths": 3, "sold": "2026-10-08", "pps": 161},
]

# Common Castle Rock streets for autocomplete
CASTLE_ROCK_ADDRESSES = [
    "290 Emerald Dr, Castle Rock, CO 80108",
    "3531 Morning Glory Drive, Castle Rock, CO 80109",
    "4350 Old Windmill Way, Castle Rock, CO 80109",
    "6014 Hoofbeat Place, Castle Rock, CO 80108",
    "4812 N Silverlace Drive, Castle Rock, CO 80109",
    "1178 N Deckers Pl, Castle Rock, CO 80104",
    "6052 Wescroft Avenue, Castle Rock, CO 80104",
    "4219 Dunsinane Way, Castle Rock, CO 80104",
    "5302 Danvers Court, Castle Rock, CO 80104",
    "4068 Silver Swan Place, Castle Rock, CO 80109",
    "2450 Garganey Drive, Castle Rock, CO 80104",
    "467 Lorraway Drive, Castle Rock, CO 80108",
    "6568 Leilani Lane, Castle Rock, CO 80108",
    "5043 Vermillion Drive, Castle Rock, CO 80108",
    "355 Morning Star Way, Castle Rock, CO 80108",
]

LEADS_FILE = "leads.json"

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            return json.load(f)
    return []

def save_lead(lead):
    leads = load_leads()
    leads.append(lead)
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

import requests

def call_rentcast_api(address, beds=None, baths=None, sqft=None):
    """Call RentCast AVM endpoint. Requires RENTCAST_API_KEY environment variable."""
    if not USE_REAL_API:
        return None
    
    try:
        headers = {
            "X-Api-Key": RENTCAST_API_KEY,
            "Accept": "application/json"
        }
        params = {
            "address": address,
            "compCount": 5,
            "lookupSubjectAttributes": "true"
        }
        if beds:
            params["bedrooms"] = beds
        if baths:
            params["bathrooms"] = baths
        if sqft:
            params["squareFootage"] = sqft
        
        resp = requests.get(
            "https://api.rentcast.io/v1/avm/value",
            headers=headers,
            params=params,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"RentCast API error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"RentCast request failed: {e}")
        return None

def estimate_value(address, beds, baths, sqft, force_local=False):
    """Multi-source valuation engine that blends available data sources."""
    if not sqft or sqft <= 0:
        sqft = 2300
    
    sources = []
    all_comps = []
    
    # 1. Local Castle Rock comps model
    similar = [c for c in SAMPLE_COMPS if abs(c["sqft"] - sqft) / max(sqft, 1) < 0.45]
    if not similar:
        similar = SAMPLE_COMPS
    avg_pps = sum(c["pps"] for c in similar) / len(similar)
    if beds >= 5:
        avg_pps += 6
    if baths >= 3.5:
        avg_pps += 4
    if sqft > 4000:
        avg_pps += 3
    elif sqft < 1800:
        avg_pps += 12
    local_est = int(sqft * avg_pps)
    sources.append({"name": "Local Castle Rock Comps", "value": local_est, "weight": 0.40})
    all_comps.extend(sorted(SAMPLE_COMPS, key=lambda x: abs(x["sqft"] - sqft))[:3])
    
    # 2. RentCast API (if available and not forced local)
    if not force_local and USE_REAL_API:
        api_result = call_rentcast_api(address, beds, baths, sqft)
        if api_result and "price" in api_result:
            api_est = int(api_result.get("price", 0))
            sources.append({"name": "RentCast AVM", "value": api_est, "weight": 0.45})
            for c in api_result.get("comparables", [])[:3]:
                all_comps.append({
                    "address": c.get("formattedAddress", ""),
                    "price": c.get("price", 0),
                    "sqft": c.get("squareFootage", 0),
                    "beds": c.get("bedrooms", 0),
                    "baths": c.get("bathrooms", 0),
                    "sold": (c.get("lastSaleDate") or c.get("listedDate") or "")[:10]
                })
    
    # 3. Market benchmark (Castle Rock / Douglas County median adjusted for size)
    # Based on recent data: larger homes ~$230-250/sqft
    market_pps = 242 if sqft > 3500 else 255
    market_est = int(sqft * market_pps)
    sources.append({"name": "Market Benchmark (Castle Rock)", "value": market_est, "weight": 0.15})
    
    # Blend sources
    total_weight = sum(s["weight"] for s in sources)
    blended = int(sum(s["value"] * s["weight"] for s in sources) / total_weight)
    
    # Range based on source spread
    values = [s["value"] for s in sources]
    low = int(min(values) * 0.96)
    high = int(max(values) * 1.04)
    
    # Deduplicate comps
    seen = set()
    unique_comps = []
    for c in all_comps:
        key = c.get("address", "")
        if key and key not in seen:
            seen.add(key)
            unique_comps.append(c)
    
    confidence = "High" if len(sources) >= 2 else "Medium-High"
    source_names = " + ".join(s["name"] for s in sources)
    
    return {
        "estimated": blended,
        "low": low,
        "high": high,
        "price_per_sqft": round(blended / sqft),
        "comps": unique_comps[:4],
        "confidence": confidence,
        "source": source_names,
        "sources_detail": sources
    }

def generate_explanation(address, estimate, beds, baths, sqft):
    """Expanded AI-style market narrative."""
    value = estimate["estimated"]
    low = estimate["low"]
    high = estimate["high"]
    pps = estimate["price_per_sqft"]
    source = estimate.get("source", "local data")
    
    # Market context variations
    contexts = [
        "The Castle Rock and southern Douglas County market continues to show balanced conditions with steady buyer interest in single-family homes.",
        "Recent transaction volume in the area indicates healthy demand, particularly for homes that are well-maintained and priced in line with recent comps.",
        "Douglas County has seen modest year-over-year appreciation, with inventory levels supporting current price stability.",
        "Local market activity remains solid, with homes in popular neighborhoods like those near Emerald, Silverlace, and Morning Glory seeing consistent interest."
    ]
    context = random.choice(contexts)
    
    # Size and feature notes
    notes = []
    if sqft > 3200:
        notes.append("Larger homes in this size range typically trade at a slightly lower price-per-square-foot but can attract families seeking more space.")
    elif sqft < 1800:
        notes.append("More compact homes often appeal to first-time buyers and downsizers, supporting strong demand in this segment.")
    else:
        notes.append("This size range is among the most liquid in the Castle Rock market.")
    
    if beds >= 4:
        notes.append("Four-plus bedroom homes remain popular with growing families.")
    
    note_text = " ".join(notes)
    
    equity_note = f"Based on typical recent sales, homeowners in this area who purchased 3–5 years ago may have seen meaningful equity growth."
    
    return (
        f"Based on a blended analysis of {source}, the estimated current market value for {address} is ${value:,}. "
        f"A realistic range given recent activity is ${low:,} to ${high:,} (approximately ${pps}/sq ft). "
        f"{context} {note_text} "
        f"{equity_note} "
        f"Final sale price will be influenced by the property’s condition, any recent updates, lot characteristics, and buyer competition at the time of listing. "
        f"This automated multi-source estimate is for informational purposes only and is not an appraisal."
    )

@app.route("/")
def index():
    return render_template("index.html", addresses=CASTLE_ROCK_ADDRESSES)

@app.route("/estimate", methods=["POST"])
def estimate():
    data = request.json
    address = data.get("address", "").strip()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    beds = int(data.get("beds") or 3)
    baths = float(data.get("baths") or 2.5)
    sqft = int(data.get("sqft") or 0)
    force_local = bool(data.get("force_local", False))
    
    if not address:
        return jsonify({"error": "Address is required"}), 400
    
    estimate_result = estimate_value(address, beds, baths, sqft, force_local=force_local)
    explanation = generate_explanation(address, estimate_result, beds, baths, sqft)
    
    # Score the lead
    intent = data.get("intent", "")
    has_phone = bool(phone and phone.strip())
    if intent == "Yes" and has_phone:
        score = "Hot"
    elif intent in ("Yes", "Maybe") or has_phone:
        score = "Warm"
    else:
        score = "Cold"
    
    # Capture source from query param or form
    source_param = request.args.get("src") or data.get("src", "direct")
    
    lead = {
        "timestamp": datetime.now().isoformat(),
        "address": address,
        "name": name,
        "email": email,
        "phone": phone,
        "intent": intent,
        "score": score,
        "source_channel": source_param,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "estimated_value": estimate_result["estimated"],
        "range_low": estimate_result["low"],
        "range_high": estimate_result["high"],
        "source": estimate_result.get("source", "demo")
    }
    save_lead(lead)
    
    # Lead notification (replace with real email/SMS integration)
    notify_lead(lead)
    
    return jsonify({
        "estimate": estimate_result,
        "explanation": explanation,
        "address": address
    })

def notify_lead(lead):
    """Send lead notification via SMS to 303-257-6580 and console log."""
    message = (
        f"New Home Value Lead [{lead.get('score', 'N/A')}]\n"
        f"Address: {lead.get('address')}\n"
        f"Name: {lead.get('name') or 'N/A'}\n"
        f"Email: {lead.get('email') or 'N/A'}\n"
        f"Phone: {lead.get('phone') or 'N/A'}\n"
        f"Selling Intent: {lead.get('intent') or 'N/A'}\n"
        f"Source: {lead.get('source_channel', 'direct')}\n"
        f"Estimate: ${lead.get('estimated_value'):,}"
    )
    print(f"\n=== NEW LEAD ===\n{message}\n================\n")
    
    # SMS via Twilio (set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_from = os.environ.get("TWILIO_FROM_NUMBER")
    if twilio_sid and twilio_token and twilio_from:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            client.messages.create(
                body=message,
                from_=twilio_from,
                to="+13032576580"
            )
            print("SMS sent to 303-257-6580")
        except Exception as e:
            print(f"SMS failed: {e}")
    else:
        print("Twilio credentials not set — SMS skipped. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER to enable.")

@app.route("/neighborhood/<name>")
def neighborhood(name):
    """Simple neighborhood landing page."""
    return render_template("index.html", addresses=CASTLE_ROCK_ADDRESSES, neighborhood=name.replace("-", " ").title())

@app.route("/leads")
def view_leads():
    leads = load_leads()
    return render_template("leads.html", leads=leads[::-1])

@app.route("/export-leads")
def export_leads():
    leads = load_leads()
    output = StringIO()
    if leads:
        writer = csv.DictWriter(output, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)
    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=home-value-leads.csv"}
    )

@app.route("/addresses")
def get_addresses():
    return jsonify(CASTLE_ROCK_ADDRESSES)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)