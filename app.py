import os
import re
from datetime import datetime, timezone
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient

# ─── BOT TEXT ───────────────────────────────────────────────────────
BOT_TEXT = {
    "main_menu": (
        "🍫 Welcome to *Luster Chocolate* 🍫\n"
        "_Tree-to-Bar Handcrafted Excellence from Côte d'Ivoire_\n\n"
        "Choose an option:\n"
        "1️⃣ Shop Our Products\n"
        "2️⃣ Contact Information\n"
        "3️⃣ About Luster Chocolate\n"
        "4️⃣ Store Hours & Location\n"
        "5️⃣ My Cart 🛒"
    ),
    "invalid": "❌ Please enter a valid option number (1-5).",
    "contact_info": (
        "📞 *Contact Luster Chocolate*\n\n"
        "📱 Phone: +225 07 88 04 67 36\n"
        "📱 Phone: +225 01 40 45 44 40\n"
        "📧 Email: info@lusterchocolate.com\n"
        "🌐 Website: lusterchocolate.com\n\n"
        "_We're here to help with your chocolate needs!_"
    ),
    "about_us": (
        "🌟 *About Luster Chocolate* 🌟\n\n"
        "We are a leading *tree-to-bar* handcrafted chocolate manufacturer proudly based in Côte d'Ivoire, the world's largest cocoa producer.\n\n"
        "🌱 *Our Mission:* Creating exceptional chocolate while supporting local farmers and sustainable practices.\n\n"
        "🏆 *Our Promise:* Finest Ivorian cacao beans transformed into exquisite chocolates with unique tropical flavors.\n\n"
        "💚 *Our Values:* Supporting local communities, environmental sustainability, and ethical sourcing."
    ),
    "hours_location": (
        "🕒 *Store Hours*\n"
        "Monday - Friday: 9:00 AM - 5:00 PM\n"
        "Weekend: Closed\n\n"
        "📍 *Location*\n"
        "04 BP 1041 Abidjan 04\n"
        "9ème Tranche, Abidjan\n"
        "Côte d'Ivoire\n\n"
        "_Visit us for the freshest chocolate experience!_"
    ),
    "product_menu": (
        "🍫 *Luster Chocolate Collection* 🍫\n\n"
        "Navigate with numbers or use:\n"
        "◀️ *Previous* | *Next* ▶️\n"
        "*Add* to cart | *Back* to menu\n\n"
        "_Showing product 1 of 9..._"
    ),
    "cart_added": "✅ *{product}* added to your cart!\n\n",
    "cart_view": (
        "🛒 *Your Cart*\n"
        "─────────────\n"
        "{cart_items}\n"
        "─────────────\n"
        "💰 *Total: ${total}*\n\n"
        "1️⃣ Continue Shopping\n"
        "2️⃣ Proceed to Checkout\n"
        "3️⃣ Clear Cart\n"
        "4️⃣ Back to Menu"
    ),
    "cart_empty": (
        "🛒 *Your cart is empty*\n\n"
        "Start shopping to add delicious chocolates!\n\n"
        "1️⃣ Browse Products\n"
        "2️⃣ Back to Menu"
    ),
    "checkout_address": (
        "📍 *Delivery Information*\n\n"
        "Please provide your complete delivery address:\n"
        "_Include: Name, Street, Area, City, Contact Number_"
    ),
    "order_confirmation": (
        "🎉 *Order Confirmed!* 🎉\n\n"
        "Thank you for choosing Luster Chocolate!\n\n"
        "📦 Your handcrafted chocolates will be delivered within 1-2 hours.\n"
        "💳 Payment on delivery\n"
        "📱 We'll call to confirm before delivery.\n\n"
        "_Enjoy our tree-to-bar excellence!_"
    ),
    "next_steps": (
        "What would you like to do next?\n\n"
        "1️⃣ Shop Again\n"
        "2️⃣ Contact Us\n"
        "3️⃣ About Luster\n"
        "4️⃣ Main Menu"
    ),
}

# ─── PRODUCT CATALOG ─────────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "Roasted Coffee Dark Chocolate Bar",
        "price": 8.99,
        "description": "70% Ivorian dark chocolate infused with locally roasted coffee beans. A bold, aromatic experience that celebrates the rich flavors of Côte d'Ivoire.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/coffee-bar.jpg"
    },
    {
        "name": "Premium Cocoa Bar (70%)",
        "price": 9.99,
        "description": "Our signature 70% dark chocolate bar made from slow-roasted Ivorian cacao beans. Pure, intense chocolate flavor with hints of tropical fruit.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-bar.jpg"
    },
    {
        "name": "Ginger Spice Chocolate Bar",
        "price": 8.99,
        "description": "Dark chocolate meets crystallized ginger for a warming, spicy-sweet sensation. Perfect balance of heat and sweetness from local ingredients.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/ginger-bar.jpg"
    },
    {
        "name": "Cocoa Nibs Dark Chocolate Bar",
        "price": 9.99,
        "description": "Crunchy roasted cocoa nibs embedded in smooth dark chocolate. Double the cocoa intensity with satisfying texture.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/nibs-bar.jpg"
    },
    {
        "name": "Pure Cocoa Butter",
        "price_range": "$15.00 - $35.00",
        "description": "Premium food-grade cocoa butter from Ivorian cacao beans. Perfect for baking, cooking, or skincare. Available in 250g and 500g sizes.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-butter.jpg"
    },
    {
        "name": "Dark Chocolate Covered Cashews",
        "price_range": "$12.00 - $32.00",
        "description": "Premium roasted cashews enrobed in our signature dark chocolate. Available in 200g and 500g packages.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/chocolate-cashews.jpg"
    },
    {
        "name": "Roasted Cocoa Nibs (Premium Pack)",
        "price_range": "$14.00 - $28.00",
        "description": "Artisanally roasted cocoa nibs packed with antioxidants. Perfect for smoothies, baking, or healthy snacking. 250g and 500g options.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-nibs-pack.jpg"
    },
    {
        "name": "Whole Cocoa Beans",
        "price": 10.00,
        "description": "Premium dried and fermented Ivorian cocoa beans. Perfect for chocolate making enthusiasts or as a unique, nutritious snack.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-beans.jpg"
    },
    {
        "name": "Artisan Cocoa Powder",
        "price_range": "$11.00 - $24.00",
        "description": "Unsweetened, high-fat cocoa powder perfect for baking and hot chocolate. Rich, intense flavor from stone-ground Ivorian beans. 200g and 500g sizes.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-powder.jpg"
    }
]

# ─── MONGO SETUP ─────────────────────────────────────────────────────
cluster = MongoClient("mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/?retryWrites=true&w=majority")
db = cluster["Chocolate_boutique"]
users = db["users"]
orders = db["orders"]

app = Flask(__name__)

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────
def send_product(resp, idx):
    """Send product information with enhanced formatting"""
    if 0 <= idx < len(PRODUCTS):
        product = PRODUCTS[idx]
        price_text = f"${product['price']}" if 'price' in product else product['price_range']
        
        message = (
            f"🍫 *{product['name']}*\n"
            f"{'─' * 25}\n"
            f"💰 *{price_text}*\n\n"
            f"{product['description']}\n\n"
            f"📱 *Navigation:*\n"
            f"◀️ Previous | Next ▶️\n"
            f"Type *Add* to add to cart\n"
            f"Type *Back* for main menu\n\n"
            f"_Product {idx + 1} of {len(PRODUCTS)}_"
        )
        
        m = resp.message(message)
        m.media(product['image'])
    return str(resp)

def calculate_cart_total(cart_items):
    """Calculate total price for cart items"""
    total = 0
    for item in cart_items:
        for product in PRODUCTS:
            if product['name'] == item:
                if 'price' in product:
                    total += product['price']
                else:
                    # For items with price ranges, use minimum price
                    price_range = product['price_range'].replace('$', '').replace(' ', '')
                    min_price = float(price_range.split('-')[0])
                    total += min_price
                break
    return round(total, 2)

def format_cart_display(cart_items):
    """Format cart items for display"""
    if not cart_items:
        return "No items in cart"
    
    display_text = ""
    for i, item in enumerate(cart_items, 1):
        # Find price for this item
        price_text = "Price varies"
        for product in PRODUCTS:
            if product['name'] == item:
                price_text = f"${product['price']}" if 'price' in product else product['price_range']
                break
        
        display_text += f"{i}. {item}\n   {price_text}\n\n"
    
    return display_text.strip()

# ─── MAIN ROUTE ───────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def reply():
    raw = request.form.get("Body", "").strip()
    num = request.form.get("From", "").replace("whatsapp:", "")
    txt = re.sub(r"[^\w\s]", "", raw).lower()
    resp = MessagingResponse()
    user = users.find_one({"number": num})

    # ─── RESET COMMANDS ───
    if any(kw in txt for kw in ("hi", "hello", "menu", "start", "reset")):
        users.update_one(
            {"number": num},
            {"$set": {"status": "main", "cart": [], "browse_index": 0}},
            upsert=True
        )
        m = resp.message(BOT_TEXT["main_menu"])
        m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # ─── NEW USER ───
    if not user:
        m = resp.message(BOT_TEXT["main_menu"])
        m.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        users.insert_one({
            "number": num,
            "status": "main",
            "browse_index": 0,
            "cart": [],
            "messages": []
        })
        return str(resp)

    # ─── MAIN MENU ───
    if user["status"] == "main":
        if txt == "1":  # Shop Products
            users.update_one({"number": num}, {"$set": {"status": "browsing", "browse_index": 0}})
            resp.message(BOT_TEXT["product_menu"])
            return send_product(resp, 0)
        elif txt == "2":  # Contact
            resp.message(BOT_TEXT["contact_info"])
        elif txt == "3":  # About
            resp.message(BOT_TEXT["about_us"])
        elif txt == "4":  # Hours/Location
            resp.message(BOT_TEXT["hours_location"])
        elif txt == "5":  # Cart
            cart = user.get("cart", [])
            if cart:
                cart_display = format_cart_display(cart)
                total = calculate_cart_total(cart)
                resp.message(BOT_TEXT["cart_view"].format(cart_items=cart_display, total=total))
                users.update_one({"number": num}, {"$set": {"status": "cart_view"}})
            else:
                resp.message(BOT_TEXT["cart_empty"])
                users.update_one({"number": num}, {"$set": {"status": "cart_empty"}})
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── BROWSING PRODUCTS ───
    if user["status"] == "browsing":
        idx = user.get("browse_index", 0)
        
        if "next" in txt:
            idx = (idx + 1) % len(PRODUCTS)
        elif "prev" in txt or "previous" in txt:
            idx = (idx - 1) % len(PRODUCTS)
        elif "add" in txt:
            product_name = PRODUCTS[idx]["name"]
            users.update_one(
                {"number": num},
                {"$push": {"cart": product_name}}
            )
            resp.message(BOT_TEXT["cart_added"].format(product=product_name))
            return send_product(resp, idx)
        elif "back" in txt:
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
            return str(resp)
        elif txt.isdigit() and 1 <= int(txt) <= len(PRODUCTS):
            idx = int(txt) - 1
        else:
            resp.message("Use ◀️*Previous* | *Next*▶️ | *Add* | *Back*")
            return str(resp)

        users.update_one({"number": num}, {"$set": {"browse_index": idx}})
        return send_product(resp, idx)

    # ─── CART VIEW ───
    if user["status"] == "cart_view":
        if txt == "1":  # Continue Shopping
            users.update_one({"number": num}, {"$set": {"status": "browsing"}})
            return send_product(resp, user.get("browse_index", 0))
        elif txt == "2":  # Checkout
            users.update_one({"number": num}, {"$set": {"status": "checkout"}})
            resp.message(BOT_TEXT["checkout_address"])
        elif txt == "3":  # Clear Cart
            users.update_one({"number": num}, {"$set": {"cart": [], "status": "main"}})
            resp.message("🗑️ Cart cleared!\n\n" + BOT_TEXT["main_menu"])
        elif txt == "4":  # Back to Menu
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
        else: 
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── CART EMPTY ───
    if user["status"] == "cart_empty":
        if txt == "1":  # Browse Products
            users.update_one({"number": num}, {"$set": {"status": "browsing", "browse_index": 0}})
            resp.message(BOT_TEXT["product_menu"])
            return send_product(resp, 0)
        elif txt == "2":  # Back to Menu
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── CHECKOUT ───
    if user["status"] == "checkout":
        cart = user.get("cart", [])
        total = calculate_cart_total(cart)
        
        # Save order
        orders.insert_one({
            "number": num,
            "items": cart,
            "address": raw,
            "total": total,
            "time": datetime.now(timezone.utc),
            "status": "confirmed"
        })
        
        users.update_one({"number": num}, {"$set": {"status": "ordered", "cart": []}})
        resp.message(BOT_TEXT["order_confirmation"])
        return str(resp)

    # ─── AFTER ORDER ───
    if user["status"] == "ordered":
        if txt == "1":  # Shop Again
            users.update_one({"number": num}, {"$set": {"status": "browsing", "browse_index": 0}})
            resp.message(BOT_TEXT["product_menu"])
            return send_product(resp, 0)
        elif txt == "2":  # Contact
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["contact_info"])
        elif txt == "3":  # About
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["about_us"])
        elif txt == "4":  # Main Menu
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
        else:
            resp.message(BOT_TEXT["next_steps"])
        return str(resp)

    # ─── FALLBACK ───
    users.update_one(
        {"number": num},
        {"$push": {"messages": {"text": raw, "date": datetime.now(timezone.utc)}}}
    )
    resp.message("Sorry, I didn't understand. Type *menu* to see options.")
    return str(resp)
  
if __name__ == "__main__":
    # Heroku always provides PORT in the environment
    port = int(os.environ["PORT"])
    app.run(host="0.0.0.0", port=port)
