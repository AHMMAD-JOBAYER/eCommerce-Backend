"""
E-Commerce Management System - FastAPI Application
Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import sqlite3
import hashlib
import secrets

# ============================================
# MODELS AND ENUMS
# ============================================

class UserRole(str, Enum):
    CUSTOMER = "customer"
    SELLER = "seller"

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"

class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class DeliveryStatus(str, Enum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# Request Models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    full_address: Optional[str] = None
    role: UserRole

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    joining_date: date
    national_id: str
    address: Optional[str] = None

class ShopCreate(BaseModel):
    shop_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None

class CategoryCreate(BaseModel):
    category_name: str
    image: Optional[str] = None

class ProductCreate(BaseModel):
    shop_id: int
    category_id: int
    product_name: str
    description: Optional[str] = None
    image: Optional[str] = None
    price: float
    unit_price: float
    stock_quantity: int = 0

class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1

class OrderCreate(BaseModel):
    shipping_address: str
    payment_method: str

# ============================================
# DATABASE SETUP
# ============================================

DB_NAME = "ecommerce.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            gender TEXT,
            city TEXT,
            country TEXT,
            zip_code TEXT,
            full_address TEXT,
            role TEXT NOT NULL,
            password TEXT NOT NULL,
            token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone_number TEXT,
            email TEXT UNIQUE NOT NULL,
            date_of_birth DATE,
            joining_date DATE NOT NULL,
            national_id TEXT UNIQUE,
            address TEXT,
            password TEXT NOT NULL,
            token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Sellers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            seller_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            approved_by_admin_id INTEGER,
            approval_date DATE,
            is_approved BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (approved_by_admin_id) REFERENCES admins(admin_id)
        )
    """)
    
    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Shops table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            shop_name TEXT NOT NULL,
            description TEXT,
            address TEXT,
            contact_phone TEXT,
            rating REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        )
    """)
    
    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            description TEXT,
            image TEXT,
            price REAL NOT NULL,
            unit_price REAL NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            product_status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(shop_id),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)
    
    # Cart items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            price_at_addition REAL NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL,
            shipping_address TEXT NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            delivery_status TEXT DEFAULT 'processing',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)
    
    # Order details table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_details (
            order_detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount REAL DEFAULT 0.0,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            amount REAL NOT NULL,
            payment_method TEXT,
            transaction_id TEXT UNIQUE,
            transaction_status TEXT DEFAULT 'pending',
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)
    
    # Shipments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER UNIQUE NOT NULL,
            shipping_date DATE,
            carrier_name TEXT,
            tracking_number TEXT UNIQUE,
            shipping_address TEXT NOT NULL,
            delivery_status TEXT DEFAULT 'preparing',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)
    
    conn.commit()
    conn.close()

# ============================================
# AUTHENTICATION
# ============================================

security = HTTPBearer()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    conn = get_db()
    cursor = conn.cursor()
    
    user = cursor.execute(
        "SELECT * FROM users WHERE token = ?", (token,)
    ).fetchone()
    
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    return dict(user)

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    conn = get_db()
    cursor = conn.cursor()
    
    admin = cursor.execute(
        "SELECT * FROM admins WHERE token = ?", (token,)
    ).fetchone()
    
    conn.close()
    
    if not admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    
    return dict(admin)

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(title="E-Commerce Management System", version="1.0.0")

@app.on_event("startup")
def startup():
    init_db()

# ============================================
# USER ENDPOINTS (Registration & Login)
# ============================================

@app.post("/users/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister):
    """Register a new user (customer or seller)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if email exists
    existing = cursor.execute("SELECT * FROM users WHERE email = ?", (user.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_pw = hash_password(user.password)
    cursor.execute("""
        INSERT INTO users (name, email, password, phone_number, gender, city, country, 
                          zip_code, full_address, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user.name, user.email, hashed_pw, user.phone_number, user.gender, 
          user.city, user.country, user.zip_code, user.full_address, user.role))
    
    user_id = cursor.lastrowid
    
    # Create role-specific record
    if user.role == UserRole.CUSTOMER:
        cursor.execute("INSERT INTO customers (user_id) VALUES (?)", (user_id,))
    elif user.role == UserRole.SELLER:
        cursor.execute("INSERT INTO sellers (user_id) VALUES (?)", (user_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/users/login")
def login_user(credentials: UserLogin):
    """Login user and get authentication token"""
    conn = get_db()
    cursor = conn.cursor()
    
    hashed_pw = hash_password(credentials.password)
    user = cursor.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (credentials.email, hashed_pw)
    ).fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate and save token
    token = generate_token()
    cursor.execute("UPDATE users SET token = ? WHERE user_id = ?", 
                  (token, user['user_id']))
    conn.commit()
    conn.close()
    
    return {
        "message": "Login successful",
        "token": token,
        "role": user['role'],
        "user_id": user['user_id']
    }

@app.get("/users/me")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "user_id": current_user['user_id'],
        "name": current_user['name'],
        "email": current_user['email'],
        "role": current_user['role'],
        "phone_number": current_user['phone_number'],
        "city": current_user['city'],
        "country": current_user['country']
    }

# ============================================
# ADMIN ENDPOINTS
# ============================================

@app.post("/admins/register", status_code=status.HTTP_201_CREATED)
def register_admin(admin: AdminCreate):
    """Register a new admin"""
    conn = get_db()
    cursor = conn.cursor()
    
    hashed_pw = hash_password(admin.password)
    cursor.execute("""
        INSERT INTO admins (name, email, password, phone_number, date_of_birth,
                           joining_date, national_id, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (admin.name, admin.email, hashed_pw, admin.phone_number,
          admin.date_of_birth, admin.joining_date, admin.national_id, admin.address))
    
    admin_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"message": "Admin registered successfully", "admin_id": admin_id}

@app.post("/admins/login")
def login_admin(credentials: UserLogin):
    """Admin login"""
    conn = get_db()
    cursor = conn.cursor()
    
    hashed_pw = hash_password(credentials.password)
    admin = cursor.execute(
        "SELECT * FROM admins WHERE email = ? AND password = ?",
        (credentials.email, hashed_pw)
    ).fetchone()
    
    if not admin:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    token = generate_token()
    cursor.execute("UPDATE admins SET token = ? WHERE admin_id = ?",
                  (token, admin['admin_id']))
    conn.commit()
    conn.close()
    
    return {"message": "Admin login successful", "token": token, "admin_id": admin['admin_id']}

@app.get("/admins/pending-sellers")
def get_pending_sellers(current_admin: dict = Depends(get_current_admin)):
    """Get all sellers pending approval"""
    conn = get_db()
    cursor = conn.cursor()
    
    sellers = cursor.execute("""
        SELECT s.seller_id, s.user_id, u.name, u.email, u.phone_number
        FROM sellers s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.is_approved = 0
    """).fetchall()
    
    conn.close()
    return [dict(seller) for seller in sellers]

@app.post("/admins/approve-seller/{seller_id}")
def approve_seller(seller_id: int, current_admin: dict = Depends(get_current_admin)):
    """Approve a seller"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sellers 
        SET is_approved = 1, approved_by_admin_id = ?, approval_date = ?
        WHERE seller_id = ?
    """, (current_admin['admin_id'], date.today(), seller_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Seller not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Seller approved successfully"}

# ============================================
# CATEGORY ENDPOINTS
# ============================================

@app.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, current_admin: dict = Depends(get_current_admin)):
    """Create a new category (Admin only)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO categories (category_name, image) VALUES (?, ?)",
        (category.category_name, category.image)
    )
    
    category_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"message": "Category created", "category_id": category_id}

@app.get("/categories")
def get_categories():
    """Get all categories"""
    conn = get_db()
    cursor = conn.cursor()
    
    categories = cursor.execute("SELECT * FROM categories").fetchall()
    conn.close()
    
    return [dict(cat) for cat in categories]

# ============================================
# SHOP ENDPOINTS (Seller)
# ============================================

@app.post("/shops", status_code=status.HTTP_201_CREATED)
def create_shop(shop: ShopCreate, current_user: dict = Depends(get_current_user)):
    """Create a shop (Seller only)"""
    if current_user['role'] != 'seller':
        raise HTTPException(status_code=403, detail="Only sellers can create shops")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get seller_id
    seller = cursor.execute(
        "SELECT seller_id, is_approved FROM sellers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    if not seller or not seller['is_approved']:
        conn.close()
        raise HTTPException(status_code=403, detail="Seller must be approved by admin")
    
    cursor.execute("""
        INSERT INTO shops (seller_id, shop_name, description, address, contact_phone)
        VALUES (?, ?, ?, ?, ?)
    """, (seller['seller_id'], shop.shop_name, shop.description, 
          shop.address, shop.contact_phone))
    
    shop_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"message": "Shop created successfully", "shop_id": shop_id}

@app.get("/shops/my-shops")
def get_my_shops(current_user: dict = Depends(get_current_user)):
    """Get seller's shops"""
    if current_user['role'] != 'seller':
        raise HTTPException(status_code=403, detail="Only sellers can view their shops")
    
    conn = get_db()
    cursor = conn.cursor()
    
    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    shops = cursor.execute(
        "SELECT * FROM shops WHERE seller_id = ?",
        (seller['seller_id'],)
    ).fetchall()
    
    conn.close()
    return [dict(shop) for shop in shops]

@app.get("/shops")
def get_all_shops():
    """Get all shops"""
    conn = get_db()
    cursor = conn.cursor()
    
    shops = cursor.execute("SELECT * FROM shops").fetchall()
    conn.close()
    
    return [dict(shop) for shop in shops]

# ============================================
# PRODUCT ENDPOINTS
# ============================================

@app.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, current_user: dict = Depends(get_current_user)):
    """Create a product (Seller only)"""
    if current_user['role'] != 'seller':
        raise HTTPException(status_code=403, detail="Only sellers can create products")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify shop ownership
    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    shop = cursor.execute(
        "SELECT * FROM shops WHERE shop_id = ? AND seller_id = ?",
        (product.shop_id, seller['seller_id'])
    ).fetchone()
    
    if not shop:
        conn.close()
        raise HTTPException(status_code=403, detail="Shop not found or not owned by seller")
    
    cursor.execute("""
        INSERT INTO products (shop_id, category_id, product_name, description, image,
                            price, unit_price, stock_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (product.shop_id, product.category_id, product.product_name, product.description,
          product.image, product.price, product.unit_price, product.stock_quantity))
    
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"message": "Product created successfully", "product_id": product_id}

@app.get("/products")
def get_products(category_id: Optional[int] = None, shop_id: Optional[int] = None):
    """Browse all products with optional filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM products WHERE product_status = 'active'"
    params = []
    
    if category_id:
        query += " AND category_id = ?"
        params.append(category_id)
    
    if shop_id:
        query += " AND shop_id = ?"
        params.append(shop_id)
    
    products = cursor.execute(query, params).fetchall()
    conn.close()
    
    return [dict(product) for product in products]

@app.get("/products/{product_id}")
def get_product(product_id: int):
    """Get product details"""
    conn = get_db()
    cursor = conn.cursor()
    
    product = cursor.execute(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    
    conn.close()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return dict(product)

# ============================================
# CART ENDPOINTS (Customer)
# ============================================

@app.post("/cart/add")
def add_to_cart(item: CartItemAdd, current_user: dict = Depends(get_current_user)):
    """Add product to cart"""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can add to cart")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get customer_id
    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    # Get product price
    product = cursor.execute(
        "SELECT price FROM products WHERE product_id = ?", (item.product_id,)
    ).fetchone()
    
    if not product:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    
    cursor.execute("""
        INSERT INTO cart_items (customer_id, product_id, quantity, price_at_addition)
        VALUES (?, ?, ?, ?)
    """, (customer['customer_id'], item.product_id, item.quantity, product['price']))
    
    conn.commit()
    conn.close()
    
    return {"message": "Product added to cart"}

@app.get("/cart")
def get_cart(current_user: dict = Depends(get_current_user)):
    """Get customer's cart"""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers have carts")
    
    conn = get_db()
    cursor = conn.cursor()
    
    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    cart_items = cursor.execute("""
        SELECT c.*, p.product_name, p.image
        FROM cart_items c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.customer_id = ?
    """, (customer['customer_id'],)).fetchall()
    
    conn.close()
    
    return [dict(item) for item in cart_items]

@app.delete("/cart/{cart_item_id}")
def remove_from_cart(cart_item_id: int, current_user: dict = Depends(get_current_user)):
    """Remove item from cart"""
    conn = get_db()
    cursor = conn.cursor()
    
    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    cursor.execute(
        "DELETE FROM cart_items WHERE cart_item_id = ? AND customer_id = ?",
        (cart_item_id, customer['customer_id'])
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Item removed from cart"}

# ============================================
# ORDER ENDPOINTS
# ============================================

@app.post("/orders/checkout")
def checkout(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    """Checkout and create order from cart"""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers can place orders")
    
    conn = get_db()
    cursor = conn.cursor()
    
    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    # Get cart items
    cart_items = cursor.execute(
        "SELECT * FROM cart_items WHERE customer_id = ?",
        (customer['customer_id'],)
    ).fetchall()
    
    if not cart_items:
        conn.close()
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total
    total_amount = sum(item['price_at_addition'] * item['quantity'] for item in cart_items)
    
    # Create order
    cursor.execute("""
        INSERT INTO orders (customer_id, total_amount, shipping_address)
        VALUES (?, ?, ?)
    """, (customer['customer_id'], total_amount, order_data.shipping_address))
    
    order_id = cursor.lastrowid
    
    # Create order details
    for item in cart_items:
        subtotal = item['price_at_addition'] * item['quantity']
        cursor.execute("""
            INSERT INTO order_details (order_id, product_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, item['product_id'], item['quantity'], 
              item['price_at_addition'], subtotal))
    
    # Create payment
    transaction_id = f"TXN{secrets.token_hex(8).upper()}"
    cursor.execute("""
        INSERT INTO payments (order_id, customer_id, amount, payment_method, transaction_id)
        VALUES (?, ?, ?, ?, ?)
    """, (order_id, customer['customer_id'], total_amount, 
          order_data.payment_method, transaction_id))
    
    # Create shipment
    tracking_number = f"TRACK{secrets.token_hex(6).upper()}"
    cursor.execute("""
        INSERT INTO shipments (order_id, shipping_address, tracking_number)
        VALUES (?, ?, ?)
    """, (order_id, order_data.shipping_address, tracking_number))
    
    # Clear cart
    cursor.execute("DELETE FROM cart_items WHERE customer_id = ?", 
                  (customer['customer_id'],))
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Order placed successfully",
        "order_id": order_id,
        "total_amount": total_amount,
        "transaction_id": transaction_id,
        "tracking_number": tracking_number
    }

@app.get("/orders/my-orders")
def get_my_orders(current_user: dict = Depends(get_current_user)):
    """Get customer's orders"""
    if current_user['role'] != 'customer':
        raise HTTPException(status_code=403, detail="Only customers have orders")
    
    conn = get_db()
    cursor = conn.cursor()
    
    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user['user_id'],)
    ).fetchone()
    
    orders = cursor.execute("""
        SELECT o.*, p.transaction_id, s.tracking_number
        FROM orders o
        LEFT JOIN payments p ON o.order_id = p.order_id
        LEFT JOIN shipments s ON o.order_id = s.order_id
        WHERE o.customer_id = ?
        ORDER BY o.order_date DESC
    """, (customer['customer_id'],)).fetchall()
    
    conn.close()
    
    return [dict(order) for order in orders]

@app.get("/orders/{order_id}")
def get_order_details(order_id: int, current_user: dict = Depends(get_current_user)):
    """Get order details"""
    conn = get_db()
    cursor = conn.cursor()
    
    order = cursor.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_items = cursor.execute("""
        SELECT od.*, p.product_name, p.image
        FROM order_details od
        JOIN products p ON od.product_id = p.product_id
        WHERE od.order_id = ?
    """, (order_id,)).fetchall()
    
    payment = cursor.execute(
        "SELECT * FROM payments WHERE order_id = ?", (order_id,)
    ).fetchone()
    
    shipment = cursor.execute(
        "SELECT * FROM shipments WHERE order_id = ?", (order_id,)
    ).fetchone()
    
    conn.close()
    
    return {
        "order": dict(order),
        "items": [dict(item) for item in order_