"""
app.py
------
Flask server for phishing simulation landing and awareness pages.
Handles: /redirect (login page), /login (POST, logs), awareness.html
"""

from flask import Flask, render_template, request, redirect, url_for
from encrypt_utils import decrypt_token
from db_utils import log_campaign_tracking, log_login_attempt

app = Flask(__name__)

@app.route("/")
def home():
    return "WPS Awareness Server is running!"

@app.route("/redirect")
def redirect_to_login():
    token = request.args.get("data")
    user_id, campaign_id = decrypt_token(token)
    if not user_id or not campaign_id:
        return "Invalid or expired link. Please contact your IT/security team.", 400
    # Mark as "opened" in campaign_tracking
    log_campaign_tracking(user_id, campaign_id, opened=True)
    return render_template("login.html", user_id=user_id, campaign_id=campaign_id)

@app.route("/login", methods=["POST"])
def phishing_login():
    user_id = request.form.get("user_id")
    campaign_id = request.form.get("campaign_id")
    submitted_email = request.form.get("submitted_email")
    submitted_pass = request.form.get("submitted_pass", "")
    # Log login attempt (user_id, campaign_id, email, pass, user_agent, ip)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    ip_address = request.remote_addr or "Unknown"
    log_login_attempt(user_id, campaign_id, submitted_email, submitted_pass, user_agent, ip_address)
    # Mark as "compromised" in campaign_tracking
    log_campaign_tracking(user_id, campaign_id, compromised=True)
    return render_template("awareness.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
