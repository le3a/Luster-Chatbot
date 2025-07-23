
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
from datetime import datetime, timezone
import re
from langdetect import detect, LangDetectException

# ─── 1) AUTO‐DETECT HELPER ─────────────────────────────────────
def detect_lang(text):
    """Return 'fr' if French detected, otherwise 'en'."""
    try:
        code = detect(text) 
    except LangDetectException:
        return "en"
    return "fr" if code.startswith("fr") else "en"
# ─────────────────────────────────────────────────────────────

# ─── 2) YOUR BOT TEXT IN BOTH LANGUAGES ──────────────────────
BOT_TEXT = {
    "en": {
        "main_menu": (
            "Hi, thanks for contacting *Luster Chocolate*.\n"
            "You can choose from one of the options below:\n\n"
            "*Type*\n"
            "1️⃣ To *contact* us\n"
            "2️⃣ To *order* our products\n"
            "3️⃣ To know our *working hours*\n"
            "4️⃣ To get our *address*"
        ),
        "invalid": "Please enter a valid option (1–4).",
        "prompt_contact": (
            "You can contact us via:\n"
            "📞 +225 07 88 04 67 36 / +225 01 40 45 44 40\n"
            "✉️ info@lusterchocolate.com"
        ),
        "ordering_mode": "You have entered *ordering mode*.",
        "order_list": (
            "Please choose a product to order:\n\n"
            "1️⃣ Roasted Coffee Bar\n"
            "2️⃣ Roasted Cocoa Bar\n"
            "3️⃣ Ginger Chocolate Bar\n"
            "4️⃣ Cocoa Nibs Bar\n"
            "5️⃣ Cocoa Butter\n"
            "6️⃣ Cashews in Dark Chocolate\n"
            "7️⃣ Cocoa Nibs (Pouch)\n"
            "8️⃣ Cocoa Beans\n"
            "9️⃣ Cocoa Powder\n"
            "0️⃣ Go back to main menu"
        ),
        "hours": "Our working hours are *9 a.m. to 5 p.m.*, Monday–Friday.",
        "address": "We’re at *04 BP 1041 Abidjan 04, Abidjan, Côte d’Ivoire*",
        "ask_address": "Please reply with your delivery address to confirm.",
        "thank_you": "Thank you! 😊 Your order will arrive within the next hour.",
        "next_steps": (
            "What would you like next?\n"
            "1️⃣ Contact us\n"
            "2️⃣ Another order\n"
            "3️⃣ Hours\n"
            "4️⃣ Address"
        )
    },
    "fr": {
        "main_menu": (
            "Bonjour, merci de contacter *Luster Chocolate*.\n"
            "Vous pouvez choisir une des options ci-dessous :\n\n"
            "*Tapez*\n"
            "1️⃣ Pour *nous contacter*\n"
            "2️⃣ Pour *commander* nos produits\n"
            "3️⃣ Pour nos *horaires*\n"
            "4️⃣ Pour notre *adresse*"
        ),
        "invalid": "Veuillez entrer une option valide (1–4).",
        "prompt_contact": (
            "Vous pouvez nous contacter via :\n"
            "📞 +225 07 88 04 67 36 / +225 01 40 45 44 40\n"
            "✉️ info@lusterchocolate.com"
        ),
        "ordering_mode": "Vous êtes en *mode commande*.",
        "order_list": (
            "Veuillez choisir un produit :\n\n"
            "1️⃣ Barre Café Torréfié\n"
            "2️⃣ Barre Cacao Torréfié\n"
            "3️⃣ Barre au Gingembre\n"
            "4️⃣ Barre de Nibs de Cacao\n"
            "5️⃣ Beurre de Cacao\n"
            "6️⃣ Noix de Cajou en Chocolat\n"
            "7️⃣ Nibs de Cacao (Sachet)\n"
            "8️⃣ Grains de Cacao\n"
            "9️⃣ Poudre de Cacao\n"
            "0️⃣ Retour au menu principal"
        ),
        "hours": "Nos horaires : *9 h à 17 h*, du lundi au vendredi.",
        "address": "Nous sommes au *04 BP 1041 Abidjan 04, Abidjan, Côte d’Ivoire*",
        "ask_address": "Merci ! Veuillez envoyer votre adresse de livraison.",
        "thank_you": "Merci ! 😊 Votre commande arrive d’ici une heure.",
        "next_steps": (
            "Que souhaitez-vous faire ?\n"
            "1️⃣ Nous contacter\n"
            "2️⃣ Nouvelle commande\n"
            "3️⃣ Horaires\n"
            "4️⃣ Adresse"
        )
    }
}
# ─────────────────────────────────────────────────────────────

# ─── 3) MONGODB SETUP ────────────────────────────────────────
cluster = MongoClient("mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/?retryWrites=true&w=majority")
db = cluster["Chocolate_boutique"]
users = db["users"]
orders = db["orders"]
# ─────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def reply():
    raw_text  = request.form.get("Body","").strip()
    number    = request.form.get("From","").replace("whatsapp:","")
    resp      = MessagingResponse()
    user      = users.find_one({"number": number})

    # ─── normalize & detect ───────────────────────────────────
    normalized = re.sub(r'[^\w\s]', '', raw_text).lower()
    lang       = detect_lang(raw_text)
    texts      = BOT_TEXT[lang]
    # ──────────────────────────────────────────────────────────

    # reset‐to‐main on greetings/menu keywords
    if any(kw in normalized for kw in ("hi","hello","menu","start","main","option","options")):
        users.update_one({"number": number}, {"$set": {"status":"main"}}, upsert=True)
        msg = resp.message(texts["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # new user → show main menu
    if user is None:
        msg = resp.message(texts["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        users.insert_one({"number":number, "status":"main", "messages":[]})
        return str(resp)

    # main‐menu logic
    if user["status"] == "main":
        try:
            opt = int(normalized)
        except ValueError:
            msg = resp.message(texts["main_menu"])
            msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
            return str(resp)

        if opt == 1:
            resp.message(texts["prompt_contact"])
        elif opt == 2:
            resp.message(texts["ordering_mode"])
            users.update_one({"number":number},{"$set":{"status":"ordering"}})
            resp.message(texts["order_list"])
        elif opt == 3:
            resp.message(texts["hours"])
        elif opt == 4:
            resp.message(texts["address"])
        else:
            resp.message(texts["invalid"])
        return str(resp)

    # ordering
    if user["status"] == "ordering":
        try:
            choice = int(normalized)
        except ValueError:
            resp.message(texts["invalid"])
            return str(resp)

        if choice == 0:
            users.update_one({"number":number},{"$set":{"status":"main"}})
            msg = resp.message(texts["main_menu"])
            msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        elif 1 <= choice <= 9:
            selected = [
                "Roasted Coffee Bar","Roasted Cocoa Bar","Ginger Chocolate Bar",
                "Cocoa Nibs Bar","Cocoa Butter","Cashews in Chocolate",
                "Cocoa Nibs (Pouch)","Cocoa Beans","Cocoa Powder"
            ][choice-1]
            users.update_one({"number":number},{"$set":{"status":"address","item":selected}})
            resp.message(f"✅ {selected} selected.")
            resp.message(texts["ask_address"])
        else:
            resp.message(texts["invalid"])
        return str(resp)

    # address collection
    if user["status"] == "address":
        sel = user.get("item","Unknown")
        resp.message(texts["thank_you"])
        orders.insert_one({
            "number":number, "item":sel,
            "address":raw_text,
            "order_time":datetime.now(timezone.utc)
        })
        users.update_one({"number":number},{"$set":{"status":"ordered"}})
        return str(resp)

    # ordered → next steps
    if user["status"] == "ordered":
        resp.message(texts["next_steps"])
        users.update_one({"number":number},{"$set":{"status":"main"}})
        return str(resp)

    # log every message
    users.update_one(
        {"number":number},
        {"$push":{"messages":{"text":raw_text,"date":datetime.now(timezone.utc)}}}
    )
    return str(resp)

if __name__ == "__main__":
    app.run(port=5000)
    
if __name__ == "__main__":
    app.run()  
