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
        "image": "https://images.unsplash.com/photo-1610450949065-1f2841536c88?w=800&h=600&fit=crop"
    },
    {
        "name": "Premium Cocoa Bar (70%)",
        "price": 9.99,
        "description": "Our signature 70% dark chocolate bar made from slow-roasted Ivorian cacao beans. Pure, intense chocolate flavor with hints of tropical fruit and earthy undertones. Each bar represents hours of careful craftsmanship from bean to bar.",
        "image": "https://images.unsplash.com/photo-1511381939415-e44015466834?w=800&h=600&fit=crop"
    },
    {
        "name": "Ginger Spice Chocolate Bar",
        "price": 8.99,
        "description": "Dark chocolate meets crystallized ginger for a warming, spicy-sweet sensation. Perfect balance of heat and sweetness from local ingredients. The ginger adds a delightful zing that complements the rich cocoa perfectly.",
        "image": "https://images.unsplash.com/photo-1549007953-2f2dc0b24019?w=800&h=600&fit=crop"
    },
    {
        "name": "Cocoa Nibs Dark Chocolate Bar",
        "price": 9.99,
        "description": "Crunchy roasted cocoa nibs embedded in smooth dark chocolate. Double the cocoa intensity with satisfying texture. These roasted nibs provide bursts of pure chocolate flavor and a delightful crunch in every bite.",
        "image": "https://images.unsplash.com/photo-1582058091505-f87a2e55a40f?w=800&h=600&fit=crop"
    },
    {
        "name": "Pure Cocoa Butter",
        "price_range": "$15.00 - $35.00",
        "price": 25.00,  # Average price for calculations
        "description": "Premium food-grade cocoa butter from Ivorian cacao beans. Perfect for baking, cooking, or skincare. Available in 250g and 500g sizes. This pure, unrefined cocoa butter retains all its natural properties and delicate chocolate aroma.",
        "image": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop"
    },
    {
        "name": "Dark Chocolate Covered Cashews",
        "price_range": "$12.00 - $32.00",
        "price": 22.00,  # Average price for calculations
        "description": "Premium roasted cashews enrobed in our signature dark chocolate. Available in 200g and 500g packages. Each cashew is carefully roasted to perfection before being coated in our smooth, rich chocolate.",
        "image": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?w=800&h=600&fit=crop"
    },
    {
        "name": "Roasted Cocoa Nibs (Premium Pack)",
        "price_range": "$14.00 - $28.00",
        "price": 21.00,  # Average price for calculations
        "description": "Artisanally roasted cocoa nibs packed with antioxidants. Perfect for smoothies, baking, or healthy snacking. 250g and 500g options. These crunchy nibs are pure chocolate essence - intense, slightly bitter, and incredibly nutritious.",
        "image": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=800&h=600&fit=crop"
    },
    {
        "name": "Whole Cocoa Beans",
        "price": 10.00,
        "description": "Premium dried and fermented Ivorian cocoa beans. Perfect for chocolate making enthusiasts or as a unique, nutritious snack. These beans showcase the terroir of Côte d'Ivoire's finest cacao growing regions.",
        "image": "https://images.unsplash.com/photo-1571115764595-644a1f56a55c?w=800&h=600&fit=crop"
    },
    {
        "name": "Artisan Cocoa Powder",
        "price_range": "$11.00 - $24.00",
        "price": 17.50,  # Average price for calculations
        "description": "Unsweetened, high-fat cocoa powder perfect for baking and hot chocolate. Rich, intense flavor from stone-ground Ivorian beans. 200g and 500g sizes. This powder delivers exceptional depth and complexity to any recipe.",
        "image": "https://images.unsplash.com/photo-1569997685772-0fb9ec1a3c8d?w=800&h=600&fit=crop"
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
            f"*Add* - Add to cart (default: 1)\n"
            f"*Add 5* - Add 5 to cart\n"
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
    """Calculate total price for cart items with quantities"""
    total = 0
    for item in cart_items:
        if isinstance(item, dict):
            # New format with quantity
            product_name = item['name']
            quantity = item.get('quantity', 1)
        else:
            # Legacy format (string only)
            product_name = item
            quantity = 1
            
        for product in PRODUCTS:
            if product['name'] == product_name:
                total += product['price'] * quantity
                break
    return round(total, 2)

def format_cart_display(cart_items):
    """Format cart items for display with quantities"""
    if not cart_items:
        return "No items in cart"
    
    display_text = ""
    for i, item in enumerate(cart_items, 1):
        if isinstance(item, dict):
            # New format with quantity
            product_name = item['name']
            quantity = item.get('quantity', 1)
        else:
            # Legacy format (string only)
            product_name = item
            quantity = 1
            
        # Find price for this item
        unit_price = 0
        for product in PRODUCTS:
            if product['name'] == product_name:
                unit_price = product['price']
                break
        
        total_price = unit_price * quantity
        display_text += f"{i}. {product_name}\n"
        display_text += f"   Qty: {quantity} × ${unit_price} = ${total_price:.2f}\n"
        display_text += f"   Type *remove {i}* to remove\n\n"
    
    return display_text.strip()

def find_product_by_name(product_name):
    """Find product by partial name match"""
    product_name_lower = product_name.lower()
    for i, product in enumerate(PRODUCTS):
        if product_name_lower in product['name'].lower():
            return i, product
    return None, None

def parse_quantity_command(text):
    """Parse commands like 'add 5', '10 cocoa butter', etc."""
    text = text.strip()
    
    # Pattern 1: "add 5" or "add"
    if text.startswith('add'):
        parts = text.split()
        if len(parts) == 1:
            return 1, None  # Just "add"
        elif len(parts) == 2 and parts[1].isdigit():
            return int(parts[1]), None  # "add 5"
    
    # Pattern 2: "5 cocoa butter" or "cocoa butter"
    parts = text.split()
    if parts and parts[0].isdigit():
        quantity = int(parts[0])
        product_name = ' '.join(parts[1:])
        return quantity, product_name
    else:
        # No quantity specified, assume 1
        return 1, text

def add_to_cart(user_cart, product_name, quantity=1):
    """Add item to cart with quantity support"""
    # Find if product already exists in cart
    for item in user_cart:
        if isinstance(item, dict) and item['name'] == product_name:
            item['quantity'] += quantity
            return user_cart
        elif isinstance(item, str) and item == product_name:
            # Convert old format to new format
            user_cart.remove(item)
            user_cart.append({'name': product_name, 'quantity': quantity + 1})
            return user_cart
    
    # Add new item
    user_cart.append({'name': product_name, 'quantity': quantity})
    return user_cart

def remove_from_cart(user_cart, index):
    """Remove item from cart by index"""
    if 1 <= index <= len(user_cart):
        removed_item = user_cart.pop(index - 1)
        return user_cart, removed_item
    return user_cart, None

def show_cart_management(resp, cart_items):
    """Display cart with management options"""
    if not cart_items:
        resp.message(BOT_TEXT["cart_empty"])
        return str(resp)
    
    cart_display = format_cart_display(cart_items)
    total = calculate_cart_total(cart_items)
    
    cart_msg = (
        f"🛒 *Your Cart* 🛒\n"
        f"{'─' * 25}\n"
        f"{cart_display}\n"
        f"{'─' * 25}\n"
        f"💰 *Total: ${total}*\n\n"
        f"*Commands:*\n"
        f"• *remove 1* - Remove item #1\n"
        f"• *add [quantity] [product]* - Add more items\n"
        f"• *checkout* - Proceed to checkout\n"
        f"• *clear* - Clear entire cart\n"
        f"• *back* - Return to menu"
    )
    resp.message(cart_msg)
    return str(resp)

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
    
    # ─── GLOBAL COMMANDS (work from any state) ───
    if any(phrase in txt for phrase in ("my cart", "cart", "show cart")):
        cart = user.get("cart", []) if user else []
        users.update_one({"number": num}, {"$set": {"status": "cart_management"}}, upsert=True)
        return show_cart_management(resp, cart)
    
    # Handle quantity commands like "10 cocoa butter"
    if re.match(r'^\d+\s+\w+', txt):
        quantity, product_name = parse_quantity_command(txt)
        idx, product = find_product_by_name(product_name)
        if product:
            cart = user.get("cart", []) if user else []
            cart = add_to_cart(cart, product['name'], quantity)
            users.update_one(
                {"number": num},
                {"$set": {"cart": cart}},
                upsert=True
            )
            add_msg = f"✅ Added {quantity}x *{product['name']}* to your cart!"
            resp.message(add_msg)
            return str(resp)
        else:
            resp.message(f"❌ Product '{product_name}' not found. Type *1* to browse products.")
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
            # Parse quantity from add command
            quantity, _ = parse_quantity_command(txt)
            product_name = PRODUCTS[idx]["name"]
            
            cart = user.get("cart", [])
            cart = add_to_cart(cart, product_name, quantity)
            
            users.update_one(
                {"number": num},
                {"$set": {"cart": cart}}
            )
            
            if quantity == 1:
                cart_msg = BOT_TEXT["cart_added"].format(product=product_name)
            else:
                cart_msg = f"✅ Added {quantity}x *{product_name}* to your cart!"
            
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

    # ─── CART MANAGEMENT ───
    if user["status"] == "cart_management":
        cart = user.get("cart", [])
        
        if txt.startswith("remove "):
            try:
                index = int(txt.split()[1])
                cart, removed_item = remove_from_cart(cart, index)
                users.update_one({"number": num}, {"$set": {"cart": cart}})
                
                if removed_item:
                    if isinstance(removed_item, dict):
                        item_name = removed_item['name']
                        quantity = removed_item.get('quantity', 1)
                        resp.message(f"🗑️ Removed {quantity}x *{item_name}* from cart")
                    else:
                        resp.message(f"🗑️ Removed *{removed_item}* from cart")
                else:
                    resp.message("❌ Invalid item number")
                
                return show_cart_management(resp, cart)
            except (ValueError, IndexError):
                resp.message("❌ Please specify item number (e.g., 'remove 1')")
                return show_cart_management(resp, cart)
                
        elif txt == "clear":
            users.update_one({"number": num}, {"$set": {"cart": []}})
            resp.message("🗑️ Cart cleared!")
            return show_cart_management(resp, [])
            
        elif txt == "checkout":
            if cart:
                users.update_one({"number": num}, {"$set": {"status": "checkout"}})
                resp.message(BOT_TEXT["checkout_address"])
            else:
                resp.message("🛒 Your cart is empty!")
                return show_cart_management(resp, cart)
                
        elif txt == "back":
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
            
        elif txt.startswith("add "):
            # Handle adding items from cart management
            parts = txt.split()
            if len(parts) >= 3:  # "add 5 cocoa"
                try:
                    quantity = int(parts[1])
                    product_name = ' '.join(parts[2:])
                    idx, product = find_product_by_name(product_name)
                    if product:
                        cart = add_to_cart(cart, product['name'], quantity)
                        users.update_one({"number": num}, {"$set": {"cart": cart}})
                        resp.message(f"✅ Added {quantity}x *{product['name']}* to cart")
                        return show_cart_management(resp, cart)
                    else:
                        resp.message(f"❌ Product '{product_name}' not found")
                        return show_cart_management(resp, cart)
                except ValueError:
                    resp.message("❌ Invalid quantity. Use: add [number] [product name]")
                    return show_cart_management(resp, cart)
            else:
                resp.message("❌ Usage: add [quantity] [product name]")
                return show_cart_management(resp, cart)
        else:
            return show_cart_management(resp, cart)
        
        return str(resp)

    # ─── AFTER ORDER ───
    if user["status"] == "ordered":
        if txt == "1":  # Shop Again
            users.update_one({"number": num}, {"$set": {"status": "browsing", "browse_index": 0}})
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
