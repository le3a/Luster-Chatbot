import os
import re
from datetime import datetime, timezone
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
import uuid

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
    "browsing_intro": (
        "🍫 *Luster Chocolate Collection* 🍫\n"
        "_Handcrafted Excellence from Côte d'Ivoire_\n\n"
        "📱 *Navigation:*\n"
        "◀️ *Previous* | *Next* ▶️\n"
        "*Add* to cart | *Done* to checkout\n"
        "*Back* to main menu\n\n"
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
        "_Include: Name, Street, Area, City, Contact Number_\n\n"
        "Example: *John Doe, 123 Cocody Street, Abidjan, +225 XX XX XX XX*"  # Cocody is a district in Abidjan
    ),
    "payment_options": (
        "💳 *Choose Payment Method*\n\n"
        "Your Order Total: *${total}*\n\n"
        "Select your preferred payment option:\n"
        "1️⃣ Orange Money 🟠\n"
        "2️⃣ Wave 🌊\n"
        "3️⃣ Cash on Delivery 💵\n\n"
        "_All payments are secure and processed instantly_"
    ),
    "payment_orange": (
        "🟠 *Orange Money Payment*\n\n"
        "💰 Amount: *${amount}*\n"
        "📱 Please dial: *#144# {amount}#*\n"
        "💳 Merchant Code: *LUSTER001*\n\n"
        "After payment, reply with your *transaction reference* to confirm your order.\n\n"
        "_Payment Reference: {payment_ref}_"
    ),
    "payment_wave": (
        "🌊 *Wave Payment*\n\n"
        "💰 Amount: *${amount}*\n"
        "📱 Send payment to: *+225 07 88 04 67 36*\n"
        "📝 Reference: *LUSTER-{payment_ref}*\n\n"
        "After payment, reply with your *Wave transaction ID* to confirm your order."
    ),
    "payment_cod": (
        "💵 *Cash on Delivery Selected*\n\n"
        "💰 Amount to pay: *${amount}*\n"
        "🚚 Payment will be collected upon delivery\n\n"
        "Your order is confirmed! We'll deliver within 1-2 hours.\n"
        "📞 We'll call before delivery.\n\n"
        "_Order Reference: {order_ref}_"
    ),
    "payment_confirmation": (
        "🎉 *Payment Confirmed!* 🎉\n\n"
        "✅ Transaction verified\n"
        "📦 Your handcrafted chocolates are being prepared\n"
        "🚚 Delivery within 1-2 hours\n"
        "📞 We'll call before delivery\n\n"
        "_Order Reference: {order_ref}_\n"
        "_Thank you for choosing Luster Chocolate!_"
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
        "description": "70% Ivorian dark chocolate infused with locally roasted coffee beans. A bold, aromatic experience that celebrates the rich flavors of Côte d'Ivoire. Made from sustainably sourced cacao beans grown in the heart of Africa's cocoa region.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/coffee-bar.jpg"
    },
    {
        "name": "Premium Cocoa Bar (70%)",
        "price": 9.99,
        "description": "Our signature 70% dark chocolate bar made from slow-roasted Ivorian cacao beans. Pure, intense chocolate flavor with hints of tropical fruit and earthy undertones. Each bar represents hours of careful craftsmanship from bean to bar.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-bar.jpg"
    },
    {
        "name": "Ginger Spice Chocolate Bar",
        "price": 8.99,
        "description": "Dark chocolate meets crystallized ginger for a warming, spicy-sweet sensation. Perfect balance of heat and sweetness from local ingredients. The ginger adds a delightful zing that complements the rich cocoa perfectly.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/ginger-bar.jpg"
    },
    {
        "name": "Cocoa Nibs Dark Chocolate Bar",
        "price": 9.99,
        "description": "Crunchy roasted cocoa nibs embedded in smooth dark chocolate. Double the cocoa intensity with satisfying texture. These roasted nibs provide bursts of pure chocolate flavor and a delightful crunch in every bite.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/nibs-bar.jpg"
    },
    {
        "name": "Pure Cocoa Butter",
        "price_range": "$15.00 - $35.00",
        "price": 25.00,  # Average price for calculations
        "description": "Premium food-grade cocoa butter from Ivorian cacao beans. Perfect for baking, cooking, or skincare. Available in 250g and 500g sizes. This pure, unrefined cocoa butter retains all its natural properties and delicate chocolate aroma.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-butter.jpg"
    },
    {
        "name": "Dark Chocolate Covered Cashews",
        "price_range": "$12.00 - $32.00",
        "price": 22.00,  # Average price for calculations
        "description": "Premium roasted cashews enrobed in our signature dark chocolate. Available in 200g and 500g packages. Each cashew is carefully roasted to perfection before being coated in our smooth, rich chocolate.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/chocolate-cashews.jpg"
    },
    {
        "name": "Roasted Cocoa Nibs (Premium Pack)",
        "price_range": "$14.00 - $28.00",
        "price": 21.00,  # Average price for calculations
        "description": "Artisanally roasted cocoa nibs packed with antioxidants. Perfect for smoothies, baking, or healthy snacking. 250g and 500g options. These crunchy nibs are pure chocolate essence - intense, slightly bitter, and incredibly nutritious.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-nibs-pack.jpg"
    },
    {
        "name": "Whole Cocoa Beans",
        "price": 10.00,
        "description": "Premium dried and fermented Ivorian cocoa beans. Perfect for chocolate making enthusiasts or as a unique, nutritious snack. These beans showcase the terroir of Côte d'Ivoire's finest cacao growing regions.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-beans.jpg"
    },
    {
        "name": "Artisan Cocoa Powder",
        "price_range": "$11.00 - $24.00",
        "price": 17.50,  # Average price for calculations
        "description": "Unsweetened, high-fat cocoa powder perfect for baking and hot chocolate. Rich, intense flavor from stone-ground Ivorian beans. 200g and 500g sizes. This powder delivers exceptional depth and complexity to any recipe.",
        "image": "https://lusterchocolate.com/wp-content/uploads/2022/09/cocoa-powder.jpg"
    }
]

# ─── MONGO SETUP ─────────────────────────────────────────────────────
cluster = MongoClient("mongodb+srv://luster:luster@cluster0.kl9tztu.mongodb.net/?retryWrites=true&w=majority")
db = cluster["Chocolate_boutique"]
users = db["users"]
orders = db["orders"]
payments = db["payments"]

app = Flask(__name__)

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────
def send_product(resp, idx):
    """Send product information with enhanced formatting"""
    if 0 <= idx < len(PRODUCTS):
        product = PRODUCTS[idx]
        price_text = f"${product['price']}" if 'price' in product else product['price_range']
        
        # Include intro for first product
        intro_text = ""
        if idx == 0:
            intro_text = (
                f"🍫 *Luster Chocolate Collection* 🍫\n"
                f"_Handcrafted Excellence from Côte d'Ivoire_\n\n"
            )
        
        message = (
            f"{intro_text}"
            f"🍫 *{product['name']}*\n"
            f"{'─' * 30}\n"
            f"💰 *{price_text}*\n\n"
            f"{product['description']}\n\n"
            f"📱 *Commands:*\n"
            f"◀️ *Previous* | *Next* ▶️\n"
            f"*Add* - Add to cart\n"
            f"*Done* - Go to checkout\n"
            f"*Back* - Main menu\n\n"
            f"_Product {idx + 1} of {len(PRODUCTS)}_"
        )
        
        msg = resp.message(message)
        try:
            msg.media(product['image'])
        except Exception as e:
            print(f"Error attaching image for {product['name']}: {e}")
    else:
        resp.message("❌ Product not found. Type *back* to return to menu.")
    return str(resp)

def calculate_cart_total(cart_items):
    """Calculate total price for cart items"""
    total = 0
    for item in cart_items:
        for product in PRODUCTS:
            if product['name'] == item:
                total += product['price']
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

def generate_payment_reference():
    """Generate unique payment reference"""
    return str(uuid.uuid4())[:8].upper()

def generate_order_reference():
    """Generate unique order reference"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    return f"LST-{timestamp}-{str(uuid.uuid4())[:4].upper()}"

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
        msg = resp.message(BOT_TEXT["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
        return str(resp)

    # ─── NEW USER ───
    if not user:
        msg = resp.message(BOT_TEXT["main_menu"])
        msg.media("https://lusterchocolate.com/wp-content/uploads/2022/09/pr-3-3-scaled-1.jpeg")
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
            # Send intro and immediately show first product
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
                cart_view_msg = BOT_TEXT["cart_view"].format(cart_items=cart_display, total=total)
                resp.message(cart_view_msg)
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
            users.update_one({"number": num}, {"$set": {"browse_index": idx}})
            return send_product(resp, idx)
        elif "prev" in txt or "previous" in txt:
            idx = (idx - 1) % len(PRODUCTS)
            users.update_one({"number": num}, {"$set": {"browse_index": idx}})
            return send_product(resp, idx)
        elif "add" in txt:
            product_name = PRODUCTS[idx]["name"]
            users.update_one(
                {"number": num},
                {"$push": {"cart": product_name}}
            )
            cart_msg = BOT_TEXT["cart_added"].format(product=product_name)
            resp.message(cart_msg)
            return send_product(resp, idx)
        elif "done" in txt:
            cart = user.get("cart", [])
            if cart:
                users.update_one({"number": num}, {"$set": {"status": "checkout"}})
                resp.message(BOT_TEXT["checkout_address"])
            else:
                resp.message("🛒 Your cart is empty! Add some products first.\n\nType *add* to add the current product to cart.")
                return send_product(resp, idx)
        elif "back" in txt:
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
        elif txt.isdigit() and 1 <= int(txt) <= len(PRODUCTS):
            idx = int(txt) - 1
            users.update_one({"number": num}, {"$set": {"browse_index": idx}})
            return send_product(resp, idx)
        else:
            resp.message("Use: ◀️*Previous* | *Next*▶️ | *Add* | *Done* | *Back*")
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
            return send_product(resp, 0)
        elif txt == "2":  # Back to Menu
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
        else:
            resp.message(BOT_TEXT["invalid"])
        return str(resp)

    # ─── CHECKOUT ADDRESS ───
    if user["status"] == "checkout":
        cart = user.get("cart", [])
        total = calculate_cart_total(cart)
        
        # Store address and move to payment
        users.update_one(
            {"number": num}, 
            {"$set": {"status": "payment", "address": raw}}
        )
        payment_msg = BOT_TEXT["payment_options"].format(total=total)
        resp.message(payment_msg)
        return str(resp)

    # ─── PAYMENT SELECTION ───
    if user["status"] == "payment":
        cart = user.get("cart", [])
        total = calculate_cart_total(cart)
        address = user.get("address", "No address provided")
        
        if txt == "1":  # Orange Money
            payment_ref = generate_payment_reference()
            users.update_one(
                {"number": num}, 
                {"$set": {"status": "awaiting_orange_payment", "payment_ref": payment_ref}}
            )
            orange_msg = BOT_TEXT["payment_orange"].format(amount=total, payment_ref=payment_ref)
            resp.message(orange_msg)
            
            # Store payment record
            payments.insert_one({
                "number": num,
                "payment_ref": payment_ref,
                "amount": total,
                "method": "orange_money",
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            })
            
        elif txt == "2":  # Wave
            payment_ref = generate_payment_reference()
            users.update_one(
                {"number": num}, 
                {"$set": {"status": "awaiting_wave_payment", "payment_ref": payment_ref}}
            )
            wave_msg = BOT_TEXT["payment_wave"].format(amount=total, payment_ref=payment_ref)
            resp.message(wave_msg)
            
            # Store payment record
            payments.insert_one({
                "number": num,
                "payment_ref": payment_ref,
                "amount": total,
                "method": "wave",
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            })
            
        elif txt == "3":  # Cash on Delivery
            order_ref = generate_order_reference()
            
            # Create order
            orders.insert_one({
                "number": num,
                "order_ref": order_ref,
                "items": cart,
                "address": address,
                "total": total,
                "payment_method": "cash_on_delivery",
                "status": "confirmed",
                "time": datetime.now(timezone.utc)
            })
            
            users.update_one({"number": num}, {"$set": {"status": "ordered", "cart": []}})
            cod_msg = BOT_TEXT["payment_cod"].format(amount=total, order_ref=order_ref)
            resp.message(cod_msg)
        else:
            resp.message("Please select a valid payment option (1, 2, or 3)")
        return str(resp)

    # ─── AWAITING ORANGE PAYMENT ───
    if user["status"] == "awaiting_orange_payment":
        transaction_ref = raw.strip()
        if len(transaction_ref) >= 6:  # Basic validation
            payment_ref = user.get("payment_ref")
            cart = user.get("cart", [])
            total = calculate_cart_total(cart)
            address = user.get("address", "No address provided")
            order_ref = generate_order_reference()
            
            # Update payment status
            payments.update_one(
                {"payment_ref": payment_ref},
                {"$set": {"status": "confirmed", "transaction_ref": transaction_ref}}
            )
            
            # Create order
            orders.insert_one({
                "number": num,
                "order_ref": order_ref,
                "items": cart,
                "address": address,
                "total": total,
                "payment_method": "orange_money",
                "payment_ref": payment_ref,
                "transaction_ref": transaction_ref,
                "status": "confirmed",
                "time": datetime.now(timezone.utc)
            })
            
            users.update_one({"number": num}, {"$set": {"status": "ordered", "cart": []}})
            confirmation_msg = BOT_TEXT["payment_confirmation"].format(order_ref=order_ref)
            resp.message(confirmation_msg)
        else:
            resp.message("❌ Invalid transaction reference. Please provide your Orange Money transaction reference (minimum 6 characters).")
        return str(resp)

    # ─── AWAITING WAVE PAYMENT ───
    if user["status"] == "awaiting_wave_payment":
        transaction_id = raw.strip()
        if len(transaction_id) >= 6:  # Basic validation
            payment_ref = user.get("payment_ref")
            cart = user.get("cart", [])
            total = calculate_cart_total(cart)
            address = user.get("address", "No address provided")
            order_ref = generate_order_reference()
            
            # Update payment status
            payments.update_one(
                {"payment_ref": payment_ref},
                {"$set": {"status": "confirmed", "transaction_id": transaction_id}}
            )
            
            # Create order
            orders.insert_one({
                "number": num,
                "order_ref": order_ref,
                "items": cart,
                "address": address,
                "total": total,
                "payment_method": "wave",
                "payment_ref": payment_ref,
                "transaction_id": transaction_id,
                "status": "confirmed",
                "time": datetime.now(timezone.utc)
            })
            
            users.update_one({"number": num}, {"$set": {"status": "ordered", "cart": []}})
            wave_confirmation_msg = BOT_TEXT["payment_confirmation"].format(order_ref=order_ref)
            resp.message(wave_confirmation_msg)
        else:
            resp.message("❌ Invalid Wave transaction ID. Please provide your Wave transaction ID (minimum 6 characters).")
        return str(resp)

    # ─── AFTER ORDER ───
    if user["status"] == "ordered":
        if txt == "1":  # Shop Again
            users.update_one({"number": num}, {"$set": {"status": "browsing", "browse_index": 0}})
            resp.message(BOT_TEXT["browsing_intro"])
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
