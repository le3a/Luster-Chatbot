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
    "product_menu": (
        "🍫 *Luster Chocolate Collection* 🍫\n"
        "_Handcrafted Excellence from Côte d'Ivoire_\n\n"
        "*1.* Roasted Coffee 70% Cocoa - *$2.99*\n"
        "70% dark chocolate infused with perfectly roasted coffee beans\n\n"
        "*2.* Roasted Cocoa 70% Cocoa - *$2.99*\n"
        "Our signature 70% cocoa dark chocolate bar\n\n"
        "*3.* Ginger 70% Cocoa - *$2.99*\n"
        "Rich dark chocolate meets zesty ginger for a spicy-sweet treat\n\n"
        "*4.* Cocoa Nibs 70% Cocoa - *$2.99*\n"
        "Crunchy cocoa nibs enrobed in dark chocolate\n\n"
        "*5.* Pure Cocoa Butter - *$12.00*\n"
        "100% natural and unrefined cocoa butter for baking & skincare\n\n"
        "*6.* Premium Cocoa Powder - *$7.00*\n"
        "Rich, unsweetened cocoa powder for baking and hot chocolate\n\n"
        "*7.* Roasted Cocoa Nibs Pack - *$11.50*\n"
        "Artisanally roasted cocoa nibs packed with antioxidants\n\n"
        "💡 *How to Order:*\n"
        "• Single item: *1* or *3 Ginger*\n"
        "• Multiple items: *3 Cocoa Butter, 6 Roasted Nibs, done*\n"
        "• Just type product numbers or names separated by commas\n\n"
        "🛒 *My Cart:* Type *cart* | ✅ *Checkout:* Type *done*"
    ),
    "items_added": "✅ Added {items} to your cart!\n\n🛒 *Would you like to add anything else?*\n\nContinue ordering or type *done* to checkout.",
    "cart_view": (
        "🛒 *Your Cart*\n"
        "─────────────\n"
        "{cart_items}\n"
        "─────────────\n"
        "💰 *Total: ${total}*\n\n"
        "1️⃣ Add more items\n"
        "2️⃣ Checkout\n"
        "3️⃣ Clear cart\n"
        "4️⃣ Main menu"
    ),
    "cart_empty": (
        "🛒 *Your cart is empty*\n\n"
        "Start shopping to add delicious chocolates!\n\n"
        "1️⃣ Browse Products\n"
        "2️⃣ Main Menu"
    ),
    "checkout_address": (
        "📍 *Delivery Information*\n\n"
        "Please provide your complete delivery address:\n"
        "_Include: Name, Street, Area, City, Contact Number_\n\n"
        "Example: *John Doe, 123 Cocody Street, Abidjan, +225 XX XX XX XX*"
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
    "invalid_product": "❌ Try: *1-7*, product names, or *3 Cocoa Butter, 2 Nibs, done*",
}

# ─── PRODUCT SHORTCUTS ─────────────────────────────────────────────────
PRODUCT_ALIASES = {
    # Single word shortcuts
    "coffee": 0, "cocoa": 1, "ginger": 2, "nibs": 3, "butter": 4, "powder": 5, "roasted": 6,
    # Partial matches for better search
    "bar": [0, 1, 2, 3], "dark": [0, 1, 2, 3], "chocolate": [0, 1, 2, 3],
    "70": [0, 1, 2, 3], "pack": 6, "premium": 5, "pure": 4,
    # Alternative names
    "bean": 0, "beans": 0, "cacao": [1, 3, 4, 5, 6]
}

# ─── PRODUCT CATALOG ─────────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "Roasted Coffee 70% Cocoa",
        "price": 2.99,
        "description": "70% dark chocolate infused with perfectly roasted coffee beans for a bold, aromatic flavor that celebrates the rich coffee culture of Côte d'Ivoire.",
    },
    {
        "name": "Roasted Cocoa 70% Cocoa", 
        "price": 2.99,
        "description": "Our signature 70% cocoa dark chocolate bar, made from beans slow-roasted to deepen the natural chocolate notes and showcase the terroir of Ivorian cacao.",
    },
    {
        "name": "Ginger 70% Cocoa",
        "price": 2.99,
        "description": "Rich dark chocolate meets zesty ginger for a warm, spicy-sweet treat that tingles the palate. A perfect balance of heat and sweetness from local ingredients.",
    },
    {
        "name": "Cocoa Nibs 70% Cocoa",
        "price": 2.99,
        "description": "Crunchy cocoa nibs enrobed in dark chocolate, offering an earthy texture and intense cocoa flavor. Double the cocoa intensity for true chocolate connoisseurs.",
    },
    {
        "name": "Pure Cocoa Butter",
        "price": 12.00,
        "description": "100% natural and unrefined cocoa butter sourced from finest Ivorian cacao beans. Perfect for baking, cooking, skincare, and soap making applications.",
    },
    {
        "name": "Premium Cocoa Powder",
        "price": 7.00,
        "description": "Rich, unsweetened cocoa powder perfect for baking and hot chocolate. Made from stone-ground Ivorian beans with exceptional depth and complexity.",
    },
    {
        "name": "Roasted Cocoa Nibs Pack",
        "price": 11.50,
        "description": "Artisanally roasted cocoa nibs packed with antioxidants. Perfect for smoothies, baking, or healthy snacking. Pure chocolate essence in crunchy form.",
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

def normalize_text(text):
    """Normalize text for better matching"""
    return text.lower().strip().replace('-', ' ').replace('_', ' ')

def find_product_by_name(product_name):
    """Enhanced product matching with abbreviations, typos, and aliases"""
    product_name = normalize_text(product_name)
    
    # Enhanced product matching patterns
    product_patterns = {
        0: [  # Roasted Coffee 70% Cocoa
            'roasted coffee', 'coffee', 'coffee 70', 'coffee bar', 'coffee chocolate',
            'roasted coffee 70', 'coffee cocoa', 'coffe', 'cofee'
        ],
        1: [  # Roasted Cocoa 70% Cocoa
            'roasted cocoa', 'cocoa 70', 'cocoa bar', 'dark chocolate', 'dark cocoa',
            'roasted cocoa 70', 'signature cocoa', 'plain cocoa', 'cocoa chocolate',
            'dark', '70 cocoa', 'cocoa'
        ],
        2: [  # Ginger 70% Cocoa
            'ginger', 'ginger 70', 'ginger cocoa', 'ginger chocolate', 'ginger bar',
            'spicy chocolate', 'zingy', 'ginjer', 'gingr'
        ],
        3: [  # Cocoa Nibs 70% Cocoa (bar)
            'cocoa nibs 70', 'nibs 70', 'cocoa nibs bar', 'nibs bar', 'crunchy cocoa',
            'cocoa nibs chocolate', 'nibs chocolate', 'cocoa nib', 'nibs bar', 
            'nibs chocolate bar', 'chocolate nibs'
        ],
        4: [  # Pure Cocoa Butter
            'pure cocoa butter', 'cocoa butter', 'butter', 'cacao butter', 'pure butter',
            'natural butter', 'unrefined butter', 'baking butter', 'cocoa fat',
            'coco butter', 'cacoa butter'
        ],
        5: [  # Premium Cocoa Powder
            'premium cocoa powder', 'cocoa powder', 'powder', 'cacao powder', 
            'premium powder', 'baking powder', 'chocolate powder', 'unsweetened powder',
            'cocoa dust', 'coco powder', 'cacoa powder', 'powdr'
        ],
        6: [  # Roasted Cocoa Nibs Pack
            'roasted cocoa nibs', 'cocoa nibs pack', 'nibs pack', 'roasted nibs',
            'cocoa nibs', 'nibs', 'crunchy nibs', 'antioxidant nibs', 'pure nibs',
            'raw nibs', 'nib pack', 'cocoa nib pack', 'snacking nibs',
            'roasted cocoa nibs pack'
        ]
    }
    
    # Handle special disambiguation for "nibs" - prioritize pack over bar
    if product_name in ['nibs', 'nib', 'cocoa nibs', 'cocoa nib']:
        # Check if context suggests the pack (more common when ordering raw ingredients)
        return 6, PRODUCTS[6]  # Default to Roasted Cocoa Nibs Pack
    
    # First try exact matches
    for idx, patterns in product_patterns.items():
        if product_name in patterns:
            return idx, PRODUCTS[idx]
    
    # Then try partial matches (contains)
    for idx, patterns in product_patterns.items():
        for pattern in patterns:
            if pattern in product_name or product_name in pattern:
                return idx, PRODUCTS[idx]
    
    # Try fuzzy matching for typos (simple character similarity)
    best_match = None
    best_score = 0
    
    for idx, patterns in product_patterns.items():
        for pattern in patterns:
            # Simple similarity score based on common characters
            common_chars = len(set(product_name) & set(pattern))
            max_chars = max(len(product_name), len(pattern))
            if max_chars > 0:
                score = common_chars / max_chars
                if score > 0.6 and score > best_score:  # 60% similarity threshold
                    best_score = score
                    best_match = (idx, PRODUCTS[idx])
    
    if best_match:
        return best_match
    
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



def parse_comma_separated_order(text):
    """Enhanced comma-separated order parsing"""
    text = text.strip()
    items_to_add = []
    checkout_requested = False
    
    # Split by commas and process each part
    parts = [part.strip() for part in text.split(',') if part.strip()]
    
    for part in parts:
        part_original = part
        part = normalize_text(part)
        
        # Check for checkout commands
        if any(cmd in part for cmd in ['done', 'checkout', 'buy', 'finish', 'complete', 'pay']):
            checkout_requested = True
            continue
        
        # Try to parse quantity + product name (e.g., "4 cocoa nibs", "5 pure cocoa butter")
        quantity_match = re.match(r'^(\d+)\s+(.+)$', part)
        if quantity_match:
            quantity = int(quantity_match.group(1))
            product_name = quantity_match.group(2).strip()
            
            # Handle special cases where quantity might be confused with product number
            if quantity > 20:  # If quantity seems too high, treat as invalid
                continue
                
            idx, product = find_product_by_name(product_name)
            if product:
                items_to_add.append({
                    'index': idx, 
                    'quantity': quantity,
                    'name': product['name']
                })
                continue
        
        # Try single product name or alias (no quantity specified)
        idx, product = find_product_by_name(part)
        if product:
            items_to_add.append({
                'index': idx,
                'quantity': 1,
                'name': product['name']
            })
            continue
            
        # Try number only (1-7) - direct product selection
        if part.isdigit() and 1 <= int(part) <= len(PRODUCTS):
            idx = int(part) - 1
            items_to_add.append({
                'index': idx,
                'quantity': 1,
                'name': PRODUCTS[idx]['name']
            })
            continue
        
        # If we get here, the part couldn't be parsed
        # This helps with debugging - we can log unrecognized parts
        # For production, you might want to remove this print statement
        pass  # Silently ignore unrecognized parts
    
    return items_to_add, checkout_requested

def process_comma_order(user_cart, items_to_add):
    """Process comma-separated order items with better descriptions"""
    added_descriptions = []
    
    for item in items_to_add:
        product_name = item['name']
        quantity = item['quantity']
        user_cart = add_to_cart(user_cart, product_name, quantity)
        
        if quantity == 1:
            added_descriptions.append(f"{product_name}")
        else:
            added_descriptions.append(f"{quantity}x {product_name}")
    
    return user_cart, added_descriptions

# ─── TEST ENHANCED PARSING (Remove this in production) ───
def test_parsing():
    """Test the enhanced parsing system"""
    test_cases = [
        "4 cocoa nibs",
        "5 pure cocoa butter, 6 premium cocoa powder",
        "nibs",
        "Cocoa Nibs",
        "butter",
        "powder",
        "3 ginger, 2 coffee, done"
    ]
    
    print("Testing enhanced parsing system:")
    for test in test_cases:
        print(f"\nInput: '{test}'")
        items, checkout = parse_comma_separated_order(test)
        for item in items:
            print(f"  → {item['quantity']}x {item['name']}")
        if checkout:
            print("  → Checkout requested")

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
            users.update_one({"number": num}, {"$set": {"status": "ordering"}})
            resp.message(BOT_TEXT["product_menu"])
            return str(resp)
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

    # ─── ORDERING MODE ───
    if user["status"] == "ordering":
        cart = user.get("cart", [])
        
        # Handle "done" checkout command
        if txt.lower() in ['done', 'checkout', 'buy', 'finish', 'complete']:
            if cart:
                users.update_one({"number": num}, {"$set": {"status": "checkout"}})
                resp.message(BOT_TEXT["checkout_address"])
            else:
                resp.message("🛒 Your cart is empty! Please add some products first.")
                resp.message(BOT_TEXT["product_menu"])
            return str(resp)
        
        # Handle "back" command
        if "back" in txt:
            users.update_one({"number": num}, {"$set": {"status": "main"}})
            resp.message(BOT_TEXT["main_menu"])
            return str(resp)
        
        # Handle cart view
        if txt.lower() in ['cart', 'show cart', 'my cart']:
            users.update_one({"number": num}, {"$set": {"status": "cart_view"}})
            return show_cart_management(resp, cart)
        
        # Try comma-separated order parsing first (supports "3 Cocoa Butter, 6 Roasted Nibs, done")
        if ',' in txt or any(word in txt.lower() for word in ['done', 'checkout', 'buy']):
            items_to_add, checkout_requested = parse_comma_separated_order(txt)
            
            if items_to_add:
                cart, added_descriptions = process_comma_order(cart, items_to_add)
                users.update_one({"number": num}, {"$set": {"cart": cart}})
                
                items_msg = BOT_TEXT["items_added"].format(items=", ".join(added_descriptions))
                resp.message(items_msg)
                
                # If "done" was included in the order, proceed to checkout
                if checkout_requested:
                    users.update_one({"number": num}, {"$set": {"status": "checkout"}})
                    resp.message(BOT_TEXT["checkout_address"])
                return str(resp)
        
        # Handle single number selection (1-7)
        if txt.isdigit() and 1 <= int(txt) <= len(PRODUCTS):
            product_idx = int(txt) - 1
            product_name = PRODUCTS[product_idx]["name"]
            cart = add_to_cart(cart, product_name, 1)
            
            users.update_one({"number": num}, {"$set": {"cart": cart}})
            items_msg = BOT_TEXT["items_added"].format(items=product_name)
            resp.message(items_msg)
            return str(resp)
        
        # Handle traditional quantity + product name (e.g., "3 Cocoa Butter")
        elif re.match(r'^\d+\s+\w+', txt):
            quantity, product_name = parse_quantity_command(txt)
            idx, product = find_product_by_name(product_name)
            if product:
                cart = add_to_cart(cart, product['name'], quantity)
                users.update_one({"number": num}, {"$set": {"cart": cart}})
                if quantity == 1:
                    items_msg = BOT_TEXT["items_added"].format(items=product['name'])
                else:
                    items_msg = BOT_TEXT["items_added"].format(items=f"{quantity}x {product['name']}")
                resp.message(items_msg)
            else:
                resp.message(BOT_TEXT["invalid_product"])
                resp.message(BOT_TEXT["product_menu"])
            return str(resp)
        
        # Handle product name search (e.g., "ginger", "cocoa butter")
        else:
            idx, product = find_product_by_name(txt)
            if product:
                cart = add_to_cart(cart, product['name'], 1)
                users.update_one({"number": num}, {"$set": {"cart": cart}})
                items_msg = BOT_TEXT["items_added"].format(items=product['name'])
                resp.message(items_msg)
            else:
                resp.message(BOT_TEXT["invalid_product"])
                resp.message(BOT_TEXT["product_menu"])

    # ─── CART VIEW ───
    if user["status"] == "cart_view":
        if txt == "1":  # Continue Shopping
            users.update_one({"number": num}, {"$set": {"status": "ordering"}})
            resp.message(BOT_TEXT["product_menu"])
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
            users.update_one({"number": num}, {"$set": {"status": "ordering"}})
            resp.message(BOT_TEXT["product_menu"])
        elif txt == "2":  # Main menu
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
            users.update_one({"number": num}, {"$set": {"status": "ordering"}})
            resp.message(BOT_TEXT["product_menu"])
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

# ─── MAIN APPLICATION ───────────────────────────────────────────────
if __name__ == "__main__":
    # Uncomment the line below to test parsing
    # test_parsing()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

