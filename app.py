from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
from datetime import datetime, timezone
import re
import os

# ─── BOT TEXT ─────────────────────────────────────────────────────
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
    "ordering_mode": "You have entered *ordering mode*.",
    "order_list": (
        "Please choose a product:\n"
        "1️⃣ Roasted Coffee Bar\n"
        "2️⃣ Roasted Cocoa Bar\n"
        "3️⃣ Ginger Chocolate Bar\n"
        "4️⃣ Cocoa Nibs Bar\n"
        "5️⃣ Cocoa Butter\n"
        "6️⃣ Cashews in Dark Chocolate\n"
        "7️⃣ Cocoa Nibs (Pouch)\n"
        "8️⃣ Cocoa Beans\n"
        "9️⃣ Cocoa Powder"
    ),
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
# ────────────────────────────────────────────────────────────────────

# ─── MONGODB SETUP ─────────────────────────────────────────────────
cluster = MongoClient(
    "mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/"
    "?retryWrites=true&w=majority"
)
db     = cluster["Chocolate_boutique"]
users  = db["users"]
orders = db["orders"]
# ────────────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def reply():
    raw       = request.form.get("Body","").strip()
    num       = request.form.get("From","").replace("whatsapp:","")
    txt       = re.sub(r'[^\w\s]', '', raw).lower()
    resp      = MessagingResponse()
    user      = users.find_one({"number": num})

    # ─── Reset on greetings/menu keywords ──────────────────────────
    if any(k in txt for k in ("hi","hello","menu","start")):
        users.update_one(
            {"number":num},
            {"$set":{"status":"main","cart":[]}},
            upsert=True
        )
        msg = resp.message(BOT_TEXT["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # ─── New user → main menu ──────────────────────────────────────
    if user is None:
        msg = resp.message(BOT_TEXT["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        users.insert_one({
            "number": num,
            "status": "main",
            "cart":   [],
            "messages": []
        })
        return str(resp)

    # ─── MAIN MENU logic ───────────────────────────────────────────
    if user["status"] == "main":
        if txt == "1":
            resp.message(BOT_TEXT["prompt_contact"])
        elif txt == "2":
            resp.message(BOT_TEXT["ordering_mode"])
            users.update_one(
                {"number":num},
                {"$set":{"status":"ordering","cart":[]}}
            )
            resp.message(BOT_TEXT["order_list"])
        elif txt == "3":
            resp.message(BOT_TEXT["hours"])
        elif txt == "4":
            resp.message(BOT_TEXT["address"])
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── ORDERING: select items ────────────────────────────────────
    if user["status"] == "ordering":
        try:
            choice = int(txt)
        except ValueError:
            resp.message(BOT_TEXT["invalid"])
            return str(resp)

        if 1 <= choice <= 9:
            products = [
                "Roasted Coffee Bar","Roasted Cocoa Bar","Ginger Chocolate Bar",
                "Cocoa Nibs Bar","Cocoa Butter","Cashews in Dark Chocolate",
                "Cocoa Nibs (Pouch)","Cocoa Beans","Cocoa Powder"
            ]
            selected = products[choice-1]
            # add to cart & ask if more
            users.update_one(
                {"number":num},
                {"$push":{"cart":selected},"$set":{"status":"ask_more"}}
            )
            cart = user.get("cart",[]) + [selected]
            resp.message(f"✅ *{selected}* added to your cart.")
            resp.message(BOT_TEXT["ask_more"].format(cart=", ".join(cart)))
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── ASK_MORE: anything else? ──────────────────────────────────
    if user["status"] == "ask_more":
        if txt == "1":  # yes
            users.update_one({"number":num},{"$set":{"status":"ordering"}}) 
            resp.message(BOT_TEXT["order_list"])
        elif txt == "2":  # no
            users.update_one({"number":num},{"$set":{"status":"address"}})
            resp.message(BOT_TEXT["ask_address"])
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── ADDRESS COLLECTION ────────────────────────────────────────
    if user["status"] == "address":
        cart = user.get("cart",[])
        resp.message(BOT_TEXT["thank_you"])
        orders.insert_one({
            "number": num,
            "items":  cart,
            "address": raw,
            "time":    datetime.now(timezone.utc)
        })
        users.update_one({"number":num},{"$set":{"status":"ordered","cart":[]}})
        return str(resp)

    # ─── AFTER ORDERED → next steps ────────────────────────────────
    if user["status"] == "ordered":
        resp.message(BOT_TEXT["next_steps"])
        users.update_one({"number":num},{"$set":{"status":"main"}})
        return str(resp)

    # ─── Log everything else ────────────────────────────────────────
    users.update_one(
        {"number":num},
        {"$push":{"messages":{"text":raw,"date":datetime.now(timezone.utc)}}}
    )
    return str(resp)
    
if __name__ == "__main__":
    # Heroku always provides PORT in the environment
    port = int(os.environ["PORT"])
    app.run(host="0.0.0.0", port=port)
