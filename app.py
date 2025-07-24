import os
import re
from datetime import datetime, timezone
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient

# ─── BOT TEXT ───────────────────────────────────────────────────────
BOT_TEXT = {
    "main_menu": (
        "Hi, thanks for contacting *Luster Chocolate*.\n"
        "1️⃣ Contact us\n"
        "2️⃣ Order products\n"
        "3️⃣ Working hours\n"
        "4️⃣ Address"
    ),
    "invalid":       "Please enter a valid option.",
    "prompt_contact":"📞 +225 07 88 04 67 36 / +225 01 40 45 44 40\n✉️ info@lusterchocolate.com",
    "ordering_mode": "You have entered *ordering mode*.\nUse ◀Previous  Next▶ to browse or type *Add* to select.",
    "ask_more":      "🛒 In cart: {cart}\nAnything else? 1️⃣ Yes 2️⃣ No",
    "ask_address":   "Please reply with your delivery address to confirm.",
    "thank_you":     "Thank you! 😊 Your order will arrive within the next hour.",
    "next_steps": (
        "What would you like next?\n"
        "1️⃣ Contact us\n"
        "2️⃣ Another order\n"
        "3️⃣ Working hours\n"
        "4️⃣ Address"
    ),
    "hours":         "Our working hours are *9 a.m. to 5 p.m.*, Monday–Friday.",
    "address":       "We’re at *04 BP 1041 Abidjan 04, Abidjan, Côte d’Ivoire*",
}

# ─── MONGO SETUP ─────────────────────────────────────────────────────
cluster = MongoClient("mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/?retryWrites=true&w=majority")
db     = cluster["Chocolate_boutique"]
users  = db["users"]
orders = db["orders"]

app = Flask(__name__)

# ─── HELPER: send product #idx with description only ──────────────
def send_product(resp, idx):
    if idx == 0:
        resp.message(
            "*Roasted Coffee Bar*\n"
            "------------------\n"
            "$2.99\n\n"
            "A dark chocolate bar infused with perfectly roasted coffee beans for a bold, aromatic flavor.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 1:
        resp.message(
            "*Roasted Cocoa Bar*\n"
            "------------------\n"
            "$2.99\n\n"
            "Our signature 70% cocoa dark chocolate bar, made from beans slow-roasted to deepen the natural chocolate notes.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 2:
        resp.message(
            "*Ginger Chocolate Bar*\n"
            "------------------\n"
            "$2.99\n\n"
            "Rich dark chocolate meets zesty ginger for a warm, spicy-sweet treat that tingles the palate.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 3:
        resp.message(
            "*Cocoa Nibs Bar*\n"
            "------------------\n"
            "$2.99\n\n"
            "Crunchy cocoa nibs enrobed in dark chocolate, offering an earthy texture and intense cocoa flavor.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 4:
        resp.message(
            "*Cocoa Butter*\n"
            "------------------\n"
            "$12.00–$24.00\n\n"
            "Pure, creamy cocoa butter sourced from the finest beans—perfect for baking or as a rich, velvety spread.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 5:
        resp.message(
            "*Cashews in Dark Chocolate*\n"
            "------------------\n"
            "$7.00–$27.00\n\n"
            "Roasted cashews lightly coated in our rich dark chocolate for a satisfying, crunchy snack.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 6:
        resp.message(
            "*Cocoa Nibs (Pouch)*\n"
            "------------------\n"
            "$11.50–$22.00\n\n"
            "Handpicked cocoa nibs packaged in a convenient pouch—ideal for smoothies, baking, or snacking.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 7:
        resp.message(
            "*Cocoa Beans*\n"
            "------------------\n"
            "$7.00\n\n"
            "Whole dried cocoa beans, perfect for artisanal chocolate making or a crunchy healthful snack.\n\n"
            "◀Previous  Next▶"
        )
    elif idx == 8:
        resp.message(
            "*Cocoa Powder*\n"
            "------------------\n"
            "$7.00–$17.00\n\n"
            "Rich, unsweetened cocoa powder for baking, hot cocoa, or adding a decadent twist to your recipes.\n\n"
            "◀Previous  Next▶"
        )
    return str(resp)

# ─── MAIN ROUTE ───────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def reply():
    raw = request.form.get("Body", "").strip()
    num = request.form.get("From", "").replace("whatsapp:", "")
    txt = re.sub(r"[^\w\s]", "", raw).lower()
    resp = MessagingResponse()
    user = users.find_one({"number": num})

    # — RESET on greetings/menu —
    if any(kw in txt for kw in ("hi","hello","menu","start")):
        users.update_one({"number":num},{"$set":{"status":"main","cart":[]}}, upsert=True)
        m = resp.message(BOT_TEXT["main_menu"])
        m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # — NEW USER → main menu —
    if not user:
        m = resp.message(BOT_TEXT["main_menu"])
        m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        users.insert_one({"number":num,"status":"main","browse_index":0,"cart":[],"messages":[]})
        return str(resp)

    # — MAIN MENU —
    if user["status"] == "main":
        if txt == "1":
            resp.message(BOT_TEXT["prompt_contact"] )
        elif txt == "2":
            users.update_one({"number":num},{"$set":{"status":"browsing","browse_index":0,"cart":[]}})
            resp.message(BOT_TEXT["ordering_mode"] )
            return send_product(resp, 0)
        elif txt == "3":
            resp.message(BOT_TEXT["hours"] )
        elif txt == "4":
            resp.message(BOT_TEXT["address"] )
        else:
            resp.message(BOT_TEXT["invalid"] )
        return str(resp)

    # — BROWSING MODE —
    if user["status"] == "browsing":
        idx = user.get("browse_index", 0)
        if "next" in txt:
            idx = (idx + 1) % 9
        elif "prev" in txt or "previous" in txt:
            idx = (idx - 1) % 9
        elif "add" in txt:
            names = [
                "Roasted Coffee Bar","Roasted Cocoa Bar","Ginger Chocolate Bar",
                "Cocoa Nibs Bar","Cocoa Butter","Cashews in Dark Chocolate",
                "Cocoa Nibs (Pouch)","Cocoa Beans","Cocoa Powder"
            ]
            p_name = names[idx]
            users.update_one({"number":num},{"$push":{"cart":p_name},"$set":{"status":"ask_more"}})
            cart = user.get("cart", []) + [p_name]
            resp.message(f"✅ *{p_name}* added to your cart.")
            resp.message(BOT_TEXT["ask_more"].format(cart=", ".join(cart)))
            return str(resp)
        else:
            resp.message("Type ◀Previous  Next▶ or Add.")
            return str(resp)

        users.update_one({"number":num},{"$set":{"browse_index":idx}})
        return send_product(resp, idx)

    # — ASK_MORE: anything else? —
    if user["status"] == "ask_more":
        if txt in ("1", "yes"):
            users.update_one({"number":num},{"$set":{"status":"browsing"}})
            return send_product(resp, user["browse_index"])
        elif txt in ("2", "no"):
            users.update_one({"number":num},{"$set":{"status":"address"}})
            resp.message(BOT_TEXT["ask_address"])
        else:
            resp.message(BOT_TEXT["invalid"] )
        return str(resp)

    # — ADDRESS COLLECTION —
    if user["status"] == "address":
        cart = user.get("cart", [])
        resp.message(BOT_TEXT["thank_you"] )
        orders.insert_one({"number":num,"items":cart,"address":raw,"time":datetime.now(timezone.utc)})
        users.update_one({"number":num},{"$set":{"status":"ordered","cart":[]}})
        return str(resp)

    # — AFTER ORDERED —
    if user["status"] == "ordered":
        resp.message(BOT_TEXT["next_steps"] )
        users.update_one({"number":num},{"$set":{"status":"main"}})
        return str(resp)

    # — FALLBACK: log everything —
    users.update_one({"number":num},{"$push":{"messages":{"text":raw,"date":datetime.now(timezone.utc)}}})
    return str(resp)
 
  
if __name__ == "__main__":
    # Heroku always provides PORT in the environment
    port = int(os.environ["PORT"])
    app.run(host="0.0.0.0", port=port)
