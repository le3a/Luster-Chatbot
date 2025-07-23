import os
import re
from dotenv import load_dotenv      # pip install python-dotenv
from flask import Flask, request
from pymongo import MongoClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime, timezone

# ─── CONFIGURATION ──────────────────────────────────────────────
load_dotenv()

account_sid     = os.environ["TWILIO_ACCOUNT_SID"]
auth_token      = os.environ["TWILIO_AUTH_TOKEN"]
whatsapp_number = os.environ["TWILIO_WHATSAPP_NUMBER"]  # e.g. "+1415XXXXXXX"
twilio_client   = Client(account_sid, auth_token)

cluster = MongoClient(
    "mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/"
    "?retryWrites=true&w=majority"
)
db     = cluster["Chocolate_boutique"]
users  = db["users"]
orders = db["orders"]

app = Flask(__name__)

# ─── BOT TEXT ───────────────────────────────────────────────────
BOT_TEXT = {
    "main_menu": (
        "Hi, welcome to *Luster Chocolate*!\n"
        "Choose an option:\n\n"
        "1️⃣ Contact us\n"
        "2️⃣ Order products\n"
        "3️⃣ Working hours\n"
        "4️⃣ Address"
    ),
    "invalid":      "Please enter a valid option.",
    "prompt_contact": "📞 +225 07 88 04 67 36 / +225 01 40 45 44 40\n✉️ info@lusterchocolate.com",
    "hours":        "Our working hours: *9 a.m. – 5 p.m.*, Mon–Fri.",
    "address":      "We’re at *04 BP 1041 Abidjan 04, Côte d’Ivoire*",
    "ordering_mode":"You have entered *ordering mode*.\nUse *Next* or *Prev* to browse.",
    "thank_you":    "Thank you! 😊 Your order is on its way.",
    "next_steps": (
        "What would you like next?\n"
        "1️⃣ Contact\n"
        "2️⃣ Another order\n"
        "3️⃣ Hours\n"
        "4️⃣ Address"
    )
}

# ─── PRODUCT CATALOG ────────────────────────────────────────────
PRODUCT_LIST = [
    {
        "name":  "Roasted Coffee Bar",
        "price": "$2.99",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/roasted-coffee-bar.jpg"
    },
    {
        "name":  "Roasted Cocoa Bar",
        "price": "$2.99",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/roasted-cocoa-bar.jpg"
    },
    {
        "name":  "Ginger Chocolate Bar",
        "price": "$2.99",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/ginger-chocolate-bar.jpg"
    },
    {
        "name":  "Cocoa Nibs Bar",
        "price": "$2.99",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-nibs-bar.jpg"
    },
    {
        "name":  "Cocoa Butter",
        "price": "$12.00–$24.00",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-butter.jpg"
    },
    {
        "name":  "Cashews in Dark Chocolate",
        "price": "$7.00–$27.00",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cashews-dark-chocolate.jpg"
    },
    {
        "name":  "Cocoa Nibs (Pouch)",
        "price": "$11.50–$22.00",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-nibs-pouch.jpg"
    },
    {
        "name":  "Cocoa Beans",
        "price": "$7.00",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-beans.jpg"
    },
    {
        "name":  "Cocoa Powder",
        "price": "$7.00–$17.00",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-powder.jpg"
    },
]

# ─── HELPER to send current product ────────────────────────────
def send_current_product(resp, browse_index):
    p = PRODUCT_LIST[browse_index]
    m1 = resp.message()               # media message
    m1.media(p["image"])
    # text with title, price, and controls
    resp.message(
        f"*{p['name']}*\n"
        f"{p['price']}\n\n"
        "< Prev  |  Next >"
    )
    return str(resp)


# ─── MAIN REPLY HANDLER ────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def reply():
    raw     = request.form.get("Body","").strip()
    number  = request.form.get("From","").replace("whatsapp:","")
    normalized = raw.lower()
    resp    = MessagingResponse()
    user    = users.find_one({"number": number})

    # — RESET on greetings/menu
    if any(k in normalized for k in ("hi","hello","menu","start")):
        users.update_one(
            {"number":number},
            {"$set":{"status":"main"}},
            upsert=True
        )
        msg = resp.message(BOT_TEXT["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # — NEW USER → show main menu
    if user is None:
        msg = resp.message(BOT_TEXT["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        users.insert_one({
            "number": number,
            "status": "main",
            "browse_index": 0,
            "cart": [],
            "messages": []
        })
        return str(resp)

    # — MAIN MENU logic —
    if user["status"] == "main":
        # only accept 1–4
        if normalized == "1":
            resp.message(BOT_TEXT["prompt_contact"])
        elif normalized == "2":
            # enter browsing mode
            resp.message(BOT_TEXT["ordering_mode"])
            users.update_one(
                {"number":number},
                {"$set":{"status":"browsing","browse_index":0}}
            )
            return send_current_product(resp, 0)
        elif normalized == "3":
            resp.message(BOT_TEXT["hours"])
        elif normalized == "4":
            resp.message(BOT_TEXT["address"])
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # — BROWSING MODE —
    if user["status"] == "browsing":
        idx = user.get("browse_index", 0)
        if "next" in normalized:
            idx = (idx + 1) % len(PRODUCT_LIST)
        elif "prev" in normalized or "previous" in normalized:
            idx = (idx - 1) % len(PRODUCT_LIST)
        else:
            # prompt correct usage
            resp.message("Type *Next* or *Prev* to browse.")
            return str(resp)

        # save new index & show product
        users.update_one({"number":number},{"$set":{"browse_index":idx}})
        return send_current_product(resp, idx)

    # — LOG everything else —
    users.update_one(
        {"number":number},
        {"$push":{"messages":{"text":raw,"date":datetime.now(timezone.utc)}}}
    )
    return str(resp)
    
if __name__ == "__main__":
    app.run()  
