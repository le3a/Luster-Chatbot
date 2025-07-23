import os
import re
from datetime import datetime, timezone
from flask import Flask, request
from pymongo import MongoClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# ─── Twilio REST client setup ──────────────────────────────────────
# make sure you have TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN & TWILIO_WHATSAPP_NUMBER in env
account_sid     = os.environ["TWILIO_ACCOUNT_SID"]
auth_token      = os.environ["TWILIO_AUTH_TOKEN"]
whatsapp_number = os.environ["TWILIO_WHATSAPP_NUMBER"]


# ─── Bot text (English only) ───────────────────────────────────────
BOT_TEXT = {
    "main_menu": (
        "Hi, thanks for contacting *Luster Chocolate*.\n"
        "You can choose from one of the options below:\n\n"
        "1️⃣ Contact us\n"
        "2️⃣ Order products\n"
        "3️⃣ Working hours\n"
        "4️⃣ Address"
    ),
    "invalid":      "Please enter a valid option (1–4).",
    "prompt_contact": (
        "📞 +225 07 88 04 67 36 / +225 01 40 45 44 40\n"
        "✉️ info@lusterchocolate.com"
    ),
    "ordering_mode": "You have entered *ordering mode*.",
    "ask_more":      "🛒 In cart: {cart}\nAnything else? 1️⃣ Yes 2️⃣ No",
    "ask_address":   "Please reply with your delivery address to confirm.",
    "thank_you":     "Thank you! 😊 Your order will arrive within the next hour.",
    "next_steps": (
        "What would you like next?\n"
        "1️⃣ Contact us\n"
        "2️⃣ Another order\n"
        "3️⃣ Hours\n"
        "4️⃣ Address"
    )
}

# ─── Products & prices ──────────────────────────────────────────────
PRODUCT_CATEGORIES = {
    "Chocolate Bars": [
        {"id":"1","title":"Roasted Coffee 70% Cocoa",    "description":"$2.99"},
        {"id":"2","title":"Roasted Cocoa 70% Cocoa",    "description":"$2.99"},
        {"id":"3","title":"Ginger 70% Cocoa",           "description":"$2.99"},
        {"id":"4","title":"Cocoa Nibs 70% Cocoa",       "description":"$2.99"},
    ],
    "Chocolate Pouches": [
        {"id":"5","title":"Cocoa Butter",                           "description":"$12.00 – $24.00"},
        {"id":"6","title":"Roasted Cashews in Dark Chocolate",      "description":"$7.00 – $27.00"},
        {"id":"7","title":"Roasted Cocoa Nibs",                     "description":"$11.50 – $22.00"},
        {"id":"8","title":"Roasted Cocoa Beans",                    "description":"$7.00"},
        {"id":"9","title":"Cocoa Powder 100% Natural, 0% Sugar",    "description":"$7.00 – $17.00"},
    ],
}

# ─── MongoDB setup ─────────────────────────────────────────────────
cluster = MongoClient(
    "mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/"
    "?retryWrites=true&w=majority"
)
db     = cluster["Chocolate_boutique"]
users  = db["users"]
orders = db["orders"]

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def reply():
    # get WhatsApp list‐reply ID if they tapped a List Message
    list_id = request.values.get("InteractiveReply.ListReply.Id")
    raw_in  = list_id or request.form.get("Body","").strip()
    num     = request.form.get("From","").replace("whatsapp:","")
    txt     = re.sub(r"[^\w\s]","", raw_in).lower()
    resp    = MessagingResponse()
    user    = users.find_one({"number": num})

    # ── reset on greetings / main keywords
    if any(kw in txt for kw in ("hi","hello","menu","start","main")):
        users.update_one(
            {"number":num},
            {"$set":{"status":"main","cart":[]}},
            upsert=True
        )
        m = resp.message(BOT_TEXT["main_menu"])
        m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # ── new user → main menu
    if user is None:
        m = resp.message(BOT_TEXT["main_menu"])
        m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        users.insert_one({
            "number":num, "status":"main", "cart":[], "messages":[]
        })
        return str(resp)

    # ── MAIN MENU logic
    if user["status"] == "main":
        try:
            opt = int(txt)
        except ValueError:
            m = resp.message(BOT_TEXT["main_menu"])
            m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
            return str(resp)

        if opt == 1:
            resp.message(BOT_TEXT["prompt_contact"])
        elif opt == 2:
            resp.message(BOT_TEXT["ordering_mode"])
            users.update_one({"number":num},{"$set":{"status":"ordering"}})

            # ─ send interactive List Message ───────────────────────
            twilio_client.messages.create(
                from_=f"whatsapp:{whatsapp_number}",
                to   =f"whatsapp:{num}",
                interactive={  # type: ignore
                    "type":"list",
                    "body": {"text":"Please choose a product to add to your cart:"},
                    "action":{
                        "button":"View Products",
                        "sections":[
                            {
                                "title":cat,
                                "rows":[
                                    {"id":item["id"],
                                     "title":item["title"],
                                     "description":item["description"]}
                                    for item in items
                                ]
                            }
                            for cat, items in PRODUCT_CATEGORIES.items()
                        ]
                    }
                }
            )
        elif opt == 3:
            resp.message("Our working hours are *9 a.m. to 5 p.m.*, Monday–Friday.")
        elif opt == 4:
            resp.message("We’re at *04 BP 1041 Abidjan 04, Abidjan, Côte d’Ivoire*")
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ── ORDERING MODE: they’ve tapped a list‐item or typed a number
    if user["status"] == "ordering":
        try:
            choice = int(txt)
        except ValueError:
            resp.message(BOT_TEXT["invalid"])
            return str(resp)

        # look up the product title
        selected = None
        for items in PRODUCT_CATEGORIES.values():
            for it in items:
                if it["id"] == str(choice):
                    selected = it["title"]
        if not selected:
            resp.message(BOT_TEXT["invalid"])
            return str(resp)

        # add to cart & ask if they want more
        users.update_one(
            {"number":num},
            {"$push":{"cart": selected},
             "$set": {"status":"ask_more"}}
        )
        cart = ", ".join(user.get("cart",[]) + [selected])
        resp.message(BOT_TEXT["ask_more"].format(cart=cart))
        return str(resp)

    # ── ANYTHING ELSE? ──────────────────────────────────────────────
    if user["status"] == "ask_more":
        try:
            opt = int(txt)
        except ValueError:
            resp.message(BOT_TEXT["invalid"])
            return str(resp)

        if opt == 1:
            users.update_one({"number":num},{"$set":{"status":"ordering"}})
            # resend list
            twilio_client.messages.create(
                from_=f"whatsapp:{whatsapp_number}",
                to   =f"whatsapp:{num}",
                interactive={  # type: ignore
                    "type":"list",
                    "body": {"text":"Please choose another product:"},
                    "action":{
                        "button":"View Products",
                        "sections":[
                            {
                                "title":cat,
                                "rows":[
                                    {"id":item["id"],
                                     "title":item["title"],
                                     "description":item["description"]}
                                    for item in items
                                ]
                            }
                            for cat, items in PRODUCT_CATEGORIES.items()
                        ]
                    }
                }
            )
        elif opt == 2:
            users.update_one({"number":num},{"$set":{"status":"address"}})
            resp.message(BOT_TEXT["ask_address"])
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ── ADDRESS COLLECTION ──────────────────────────────────────
    if user["status"] == "address":
        cart = user.get("cart",[])
        resp.message(BOT_TEXT["thank_you"])
        orders.insert_one({
            "number": num,
            "items":  cart,
            "address": raw_in,
            "time":    datetime.now(timezone.utc)
        })
        users.update_one(
            {"number":num},
            {"$set":{"status":"ordered", "cart":[]}}
        )
        return str(resp)

    # ── AFTER ORDERED → next steps
    if user["status"] == "ordered":
        resp.message(BOT_TEXT["next_steps"])
        users.update_one({"number":num},{"$set":{"status":"main"}})
        return str(resp)

    # ── fallback: just log it
    users.update_one(
        {"number":num},
        {"$push":{"messages":{"text":raw_in,"date":datetime.now(timezone.utc)}}}
    )
    return str(resp)
    
if __name__ == "__main__":
    app.run()  
