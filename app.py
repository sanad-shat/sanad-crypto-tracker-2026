# Student Project: CryptoVision Backend
# This Flask API connects the React app with CoinGecko and stores dashboard settings.

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json
import time
import requests

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
SETTINGS_FILE = BASE_DIR / "settings.json"
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

cached_market = {"time": 0, "data": []}
cached_pages = {}
cached_global = {"time": 0, "data": {}}
CACHE_SECONDS = 55
MAX_PER_PAGE = 250


FALLBACK_COINS = [
    {"id":"bitcoin","symbol":"btc","name":"Bitcoin","image":"https://assets.coingecko.com/coins/images/1/large/bitcoin.png","current_price":104850,"price_change_percentage_24h":1.82,"market_cap":2080000000000,"total_volume":45000000000,"market_cap_rank":1},
    {"id":"ethereum","symbol":"eth","name":"Ethereum","image":"https://assets.coingecko.com/coins/images/279/large/ethereum.png","current_price":3800,"price_change_percentage_24h":-0.74,"market_cap":458000000000,"total_volume":22000000000,"market_cap_rank":2},
    {"id":"tether","symbol":"usdt","name":"Tether","image":"https://assets.coingecko.com/coins/images/325/large/Tether.png","current_price":1.00,"price_change_percentage_24h":0.01,"market_cap":112000000000,"total_volume":65000000000,"market_cap_rank":3},
    {"id":"binancecoin","symbol":"bnb","name":"BNB","image":"https://assets.coingecko.com/coins/images/825/large/bnb-icon2_2x.png","current_price":640,"price_change_percentage_24h":0.95,"market_cap":97000000000,"total_volume":1900000000,"market_cap_rank":4},
    {"id":"solana","symbol":"sol","name":"Solana","image":"https://assets.coingecko.com/coins/images/4128/large/solana.png","current_price":164,"price_change_percentage_24h":3.25,"market_cap":76000000000,"total_volume":4100000000,"market_cap_rank":5},
    {"id":"ripple","symbol":"xrp","name":"XRP","image":"https://assets.coingecko.com/coins/images/44/large/xrp-symbol-white-128.png","current_price":0.62,"price_change_percentage_24h":-1.15,"market_cap":34000000000,"total_volume":1700000000,"market_cap_rank":6},
    {"id":"usd-coin","symbol":"usdc","name":"USDC","image":"https://assets.coingecko.com/coins/images/6319/large/usdc.png","current_price":1.00,"price_change_percentage_24h":0.0,"market_cap":33000000000,"total_volume":9000000000,"market_cap_rank":7},
    {"id":"dogecoin","symbol":"doge","name":"Dogecoin","image":"https://assets.coingecko.com/coins/images/5/large/dogecoin.png","current_price":0.15,"price_change_percentage_24h":2.2,"market_cap":22000000000,"total_volume":1200000000,"market_cap_rank":8},
    {"id":"cardano","symbol":"ada","name":"Cardano","image":"https://assets.coingecko.com/coins/images/975/large/cardano.png","current_price":0.45,"price_change_percentage_24h":-0.68,"market_cap":16000000000,"total_volume":520000000,"market_cap_rank":9},
    {"id":"tron","symbol":"trx","name":"TRON","image":"https://assets.coingecko.com/coins/images/1094/large/tron-logo.png","current_price":0.12,"price_change_percentage_24h":0.41,"market_cap":10500000000,"total_volume":380000000,"market_cap_rank":10}
]



def read_settings():
    with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def fetch_market_page(page=1, per_page=100):
    """Fetch one market page from CoinGecko."""

    page = max(1, int(page or 1))
    per_page = min(MAX_PER_PAGE, max(1, int(per_page or 100)))

    cache_key = f"{page}:{per_page}"
    now = time.time()

    if cache_key in cached_pages and now - cached_pages[cache_key]["time"] < CACHE_SECONDS:
        return cached_pages[cache_key]["data"]

    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
        "sparkline": "true",
        "price_change_percentage": "1h,24h,7d"
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        print("CoinGecko Error:", error)
        data = FALLBACK_COINS if page == 1 else []

    cached_pages[cache_key] = {
        "time": now,
        "data": data
    }

    if page == 1:
        cached_market["data"] = data
        cached_market["time"] = now

    return data


def fetch_market_data():
    """Backward-compatible helper used by the small dashboard sections."""
    return fetch_market_page(page=1, per_page=250)


@app.route("/")
def home():
    return jsonify({"message": "CryptoVision backend is running", "status": "online"})


@app.route("/api/health")
def health():
    return jsonify({"status": "online", "message": "CryptoVision API is running"})


@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    if request.method == "GET":
        return jsonify(read_settings())

    current_settings = read_settings()
    new_data = request.get_json() or {}
    current_settings.update(new_data)
    save_settings(current_settings)
    return jsonify({"message": "Settings saved successfully", "settings": current_settings})


@app.route("/api/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    filename = f"banner_{int(time.time())}_{image.filename}"
    image.save(UPLOAD_FOLDER / filename)

    settings_data = read_settings()
    settings_data["heroImage"] = f"http://127.0.0.1:5000/uploads/{filename}"
    save_settings(settings_data)

    return jsonify({"message": "Image uploaded", "imageUrl": settings_data["heroImage"]})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/api/coins")
def coins():
    settings_data = read_settings()
    selected = settings_data.get("selectedCoins", [])

    # Supports both the old dashboard limit and the new CoinGecko-like pagination.
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", request.args.get("limit", settings_data.get("coinLimit", 100))))
    search = (request.args.get("search") or "").strip().lower()

    data = fetch_market_page(page=page, per_page=per_page)

    if selected:
        selected_set = set(selected)
        data = [coin for coin in data if coin.get("id") in selected_set]

    if search:
        data = [
            coin for coin in data
            if search in (coin.get("name") or "").lower()
            or search in (coin.get("symbol") or "").lower()
        ]

    return jsonify({
        "page": page,
        "perPage": per_page,
        "count": len(data),
        "coins": data
    })


@app.route("/api/trending")
def trending():
    data = fetch_market_data()
    trending_data = sorted(data, key=lambda item: item.get("total_volume") or 0, reverse=True)[:6]
    return jsonify(trending_data)


@app.route("/api/gainers")
def gainers():
    data = fetch_market_data()
    gainers_data = sorted(data, key=lambda item: item.get("price_change_percentage_24h") or -999, reverse=True)[:6]
    return jsonify(gainers_data)


@app.route("/api/losers")
def losers():
    data = fetch_market_data()
    losers_data = sorted(data, key=lambda item: item.get("price_change_percentage_24h") or 999)[:6]
    return jsonify(losers_data)


@app.route("/api/stats")
def stats():
    now = time.time()
    if cached_global["data"] and now - cached_global["time"] < CACHE_SECONDS:
        return jsonify(cached_global["data"])

    # Global market numbers from CoinGecko.
    try:
        response = requests.get("https://api.coingecko.com/api/v3/global", timeout=15)
        response.raise_for_status()
        global_data = response.json().get("data", {})
    except requests.RequestException:
        coins = fetch_market_data()
        result = {
            "totalMarketCap": sum((coin.get("market_cap") or 0) for coin in coins),
            "totalVolume": sum((coin.get("total_volume") or 0) for coin in coins),
            "btcDominance": 58.4,
            "activeCoins": len(coins),
            "markets": 0,
            "lastUpdated": int(time.time())
        }
        cached_global["data"] = result
        cached_global["time"] = now
        return jsonify(result)

    result = {
        "totalMarketCap": global_data.get("total_market_cap", {}).get("usd", 0),
        "totalVolume": global_data.get("total_volume", {}).get("usd", 0),
        "btcDominance": round(global_data.get("market_cap_percentage", {}).get("btc", 0), 2),
        "activeCoins": global_data.get("active_cryptocurrencies", 0),
        "markets": global_data.get("markets", 0),
        "lastUpdated": int(time.time())
    }
    cached_global["data"] = result
    cached_global["time"] = now
    return jsonify(result)


@app.route("/api/coin/<coin_id>")
def coin_detail(coin_id):
    """Return detailed information for a single coin."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "true"
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        print("CoinGecko detail error:", error)
        fallback = next((coin for coin in FALLBACK_COINS if coin.get("id") == coin_id), None)
        if not fallback:
            return jsonify({"error": "Coin not found"}), 404
        data = {
            "id": fallback["id"],
            "symbol": fallback["symbol"],
            "name": fallback["name"],
            "image": {"large": fallback["image"]},
            "market_cap_rank": fallback["market_cap_rank"],
            "market_data": {
                "current_price": {"usd": fallback["current_price"]},
                "market_cap": {"usd": fallback["market_cap"]},
                "total_volume": {"usd": fallback["total_volume"]},
                "price_change_percentage_24h": fallback["price_change_percentage_24h"],
                "price_change_percentage_7d": 0,
                "price_change_percentage_30d": 0,
                "sparkline_7d": {"price": []}
            },
            "description": {"en": "Fallback data is shown because the live API is temporarily unavailable."},
            "links": {"homepage": [""]}
        }
    return jsonify(data)


@app.route("/api/coin/<coin_id>/chart")
def coin_chart(coin_id):
    """Return market chart prices for 7D, 30D, or 1Y."""
    days = request.args.get("days", "7")
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        print("CoinGecko chart error:", error)
        fallback = next((coin for coin in FALLBACK_COINS if coin.get("id") == coin_id), FALLBACK_COINS[0])
        base = fallback.get("current_price", 1)
        data = {
            "prices": [[int(time.time() - (10 - i) * 86400) * 1000, base * (1 + (i - 5) * 0.01)] for i in range(10)],
            "market_caps": [],
            "total_volumes": []
        }
    return jsonify(data)


@app.route("/api/news")
def news():
    # Simple student-friendly news section. It is written as static educational headlines.
    # This avoids requiring a paid news API key.
    return jsonify([
        {"title": "Crypto markets update live through the CoinGecko API", "tag": "Market", "text": "The platform refreshes prices automatically based on the dashboard setting."},
        {"title": "Bitcoin dominance is used as a market indicator", "tag": "Analysis", "text": "The dashboard shows BTC dominance with global market statistics."},
        {"title": "React components make the project easier to maintain", "tag": "Development", "text": "Each section is separated into reusable components for clean student code."}
    ])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
