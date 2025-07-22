from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
from datetime import datetime, timezone
import re

# — MongoDB connection (password = “luster”) —
cluster = MongoClient(
    "mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
db = cluster["Chocolate_boutique"]
users = db["users"]
orders = db["orders"]
# —————————————————————————————————————————

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def reply():
    text = request.form.get("Body", "").strip()
    number = request.form.get("From", "").replace("whatsapp:", "")
    resp = MessagingResponse()
    user = users.find_one({"number": number})

    # normalize user text: lowercase, strip punctuation/extra whitespace
    normalized = re.sub(r'[^\w\s]', '', text).strip().lower()

    # ——— MAIN MENU TEXT —————————————————————————————————
    main_menu = (
        "Hi, thanks for contacting *Luster Chocolate*.\n"
        "You can choose from one of the options below:\n\n"
        "*Type*\n"
        "1️⃣ To *contact* us\n"
        "2️⃣ To *order* our products\n"
        "3️⃣ To know our *working hours*\n"
        "4️⃣ To get our *address*"
    )
    media_url = "https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg"

    # — reset-to-main if they say any of these substrings —
    reset_keys = ("hi", "hello", "menu", "start", "main", "option", "options")
    if any(kw in normalized for kw in reset_keys):
        users.update_one(
            {"number": number},
            {"$set": {"status": "main"}},
            upsert=True
        )
        msg = resp.message(main_menu)
        msg.media(media_url)
        return str(resp)

    # — brand-new user: show main menu and insert record —
    if user is None:
        msg = resp.message(main_menu)
        msg.media(media_url)
        users.insert_one({
            "number": number,
            "status": "main",
            "messages": []
        })
        return str(resp)

    # — user in main menu: parse 1–4 —
    if user["status"] == "main":
        try:
            option = int(normalized)
        except ValueError:
            # invalid → re-show main menu
            msg = resp.message(main_menu)
            msg.media(media_url)
            return str(resp)

        if option == 1:
            resp.message(
                "You can contact us via:\n"
                "📞 +225 07 88 04 67 36 / +225 01 40 45 44 40\n"
                "✉️ info@lusterchocolate.com"
            )
        elif option == 2:
            resp.message("You have entered *ordering mode*.")
            users.update_one({"number": number}, {"$set": {"status": "ordering"}})
            resp.message(
                "Please choose a product to order:\n\n"
                "1️⃣ Roasted Coffee Chocolate Bar (70% Cocoa)\n"
                "2️⃣ Roasted Cocoa Chocolate Bar (70% Cocoa)\n"
                "3️⃣ Ginger Chocolate Bar (70% Cocoa)\n"
                "4️⃣ Cocoa Nibs Chocolate Bar (70% Cocoa)\n"
                "5️⃣ Cocoa Butter (100% Natural)\n"
                "6️⃣ Roasted Cashews Coated with Dark Chocolate\n"
                "7️⃣ Roasted Cocoa Nibs (Pouch)\n"
                "8️⃣ Roasted Cocoa Beans\n"
                "9️⃣ Cocoa Powder (100% Natural, 0% Sugar)\n"
                "0️⃣ Go back to main menu"
            )
        elif option == 3:
            resp.message("Our working hours are *9 a.m. to 5 p.m.*, Monday–Friday.")
        elif option == 4:
            resp.message(
                "We’re located at:\n"
                "*04 BP 1041 Abidjan 04, 9ème Tranche, Abidjan, Côte d’Ivoire*"
            )
        else:
            msg = resp.message(main_menu)
            msg.media(media_url)
        return str(resp)

    # — ordering in progress: parse product number —
    if user["status"] == "ordering":
        try:
            choice = int(normalized)
        except ValueError:
            resp.message("Please enter a valid product number (0–9).")
            return str(resp)

        if choice == 0:
            users.update_one({"number": number}, {"$set": {"status": "main"}})
            msg = resp.message(main_menu)
            msg.media(media_url)
        elif 1 <= choice <= 9:
            products = [
                "Roasted Coffee Chocolate Bar (70% Cocoa)",
                "Roasted Cocoa Chocolate Bar (70% Cocoa)",
                "Ginger Chocolate Bar (70% Cocoa)",
                "Cocoa Nibs Chocolate Bar (70% Cocoa)",
                "Cocoa Butter (100% Natural)",
                "Roasted Cashews Coated with Dark Chocolate",
                "Roasted Cocoa Nibs (Pouch)",
                "Roasted Cocoa Beans",
                "Cocoa Powder (100% Natural, 0% Sugar)"
            ]
            selected = products[choice - 1]
            users.update_one(
                {"number": number},
                {"$set": {"status": "address", "item": selected}}
            )
            resp.message(f"Great choice! *{selected}* selected.")
            resp.message("Please reply with your delivery address to confirm.")
        else:
            resp.message("Please select a number between 0 and 9.")
        return str(resp)

    # — collecting address: finalize order —
    if user["status"] == "address":
        selected = user.get("item", "Unknown item")
        resp.message("Thank you! 😊")
        resp.message(
            f"Your order for *{selected}* has been received and will be delivered within the next hour."
        )
        orders.insert_one({
            "number": number,
            "item": selected,
            "address": text,
            "order_time": datetime.now(timezone.utc)
        })
        users.update_one({"number": number}, {"$set": {"status": "ordered"}})
        return str(resp)

    # — order complete: prompt next action & reset to main —
    if user["status"] == "ordered":
        resp.message(
            "What would you like to do next?\n"
            "1️⃣ Contact us\n"
            "2️⃣ Place another order\n"
            "3️⃣ Hours\n"
            "4️⃣ Address"
        )
        users.update_one({"number": number}, {"$set": {"status": "main"}})
        return str(resp)

    # — always log incoming message —
    users.update_one(
        {"number": number},
        {"$push": {"messages": {"text": text, "date": datetime.now(timezone.utc)}}}
    )

    return str(resp)

if __name__ == "__main__":
    app.run()  
