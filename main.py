import secrets
import bcrypt
import sqlite3
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Database configuration
DB_NAME = "ecommerce.db"

# Security
security = HTTPBearer()

# --- Enums ---


class UserRole(str, Enum):
    CUSTOMER = "customer"
    SELLER = "seller"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# --- Pydantic Models ---


# User related models
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    full_address: Optional[str] = None
    role: UserRole


class UserLogin(BaseModel):
    email: str
    password: str


# Admin related models
class AdminCreate(BaseModel):
    name: str
    email: str
    password: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    joining_date: date
    national_id: str
    address: Optional[str] = None


# Shop related models
class ShopCreate(BaseModel):
    shop_name: str
    description: Optional[str] = None
    address: str
    contact_phone: Optional[str] = None


# Category related models
class CategoryCreate(BaseModel):
    category_name: str
    image: Optional[str] = None


class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    image: Optional[str] = None


# Product related models
class ProductCreate(BaseModel):
    shop_id: int
    category_id: int
    product_name: str
    description: Optional[str] = None
    image: Optional[str] = None
    price: float
    unit_price: float
    stock_quantity: int
    product_status: ProductStatus = ProductStatus.ACTIVE


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    price: Optional[float] = None
    unit_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    product_status: Optional[ProductStatus] = None


# Cart related models
class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1


# Order related models
class OrderCreate(BaseModel):
    shipping_address: str
    payment_method: str


# --- Database Initialization ---


def get_db():
    conn = sqlite3.connect(DB_NAME)
    # Return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
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


# --- Utility Functions ---


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def generate_token() -> str:
    return secrets.token_hex(32)


# --- Dependency Functions ---


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    token = credentials.credentials
    conn = get_db()
    cursor = conn.cursor()

    user = cursor.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    return dict(user)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    token = credentials.credentials
    conn = get_db()
    cursor = conn.cursor()

    admin = cursor.execute("SELECT * FROM admins WHERE token = ?", (token,)).fetchone()

    conn.close()

    if not admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")

    return dict(admin)


# --- FastAPI Application ---

app = FastAPI()


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


# --- Authentication Endpoints ---


@app.post("/users/register")
def register_user(user: UserRegister):
    """Register a new user (customer or seller)"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if email exists
    existing = cursor.execute(
        "SELECT * FROM users WHERE email = ?", (user.email,)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    hashed_pw = hash_password(user.password)
    cursor.execute(
        """
        INSERT INTO users (name, email, password, phone_number, gender, city, country,
                           zip_code, full_address, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            user.name,
            user.email,
            hashed_pw,
            user.phone_number,
            user.gender,
            user.city,
            user.country,
            user.zip_code,
            user.full_address,
            user.role,
        ),
    )

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

    user = cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (credentials.email,),
    ).fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_valid = bcrypt.checkpw(
        credentials.password.encode("utf-8"), user["password"].encode("utf-8")
    )

    if not password_valid:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate and save token
    token = generate_token()
    cursor.execute(
        "UPDATE users SET token = ? WHERE user_id = ?", (token, user["user_id"])
    )
    conn.commit()
    conn.close()

    return {
        "message": "Login successful",
        "token": token,
        "user_id": user["user_id"],
        "role": user["role"],
    }


@app.get("/users/profile")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    # The current_user dictionary already contains user details
    # We might want to exclude sensitive fields like password and token
    user_profile = {
        k: v for k, v in current_user.items() if k not in ["password", "token"]
    }
    return user_profile


# --- Admin Endpoints ---


@app.post("/admins/register")
def register_admin(admin: AdminCreate):
    """Register a new admin"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if email or national_id exists
    existing_email = cursor.execute(
        "SELECT * FROM admins WHERE email = ?", (admin.email,)
    ).fetchone()
    if existing_email:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_national_id = cursor.execute(
        "SELECT * FROM admins WHERE national_id = ?", (admin.national_id,)
    ).fetchone()
    if existing_national_id:
        conn.close()
        raise HTTPException(status_code=400, detail="National ID already registered")

    hashed_pw = hash_password(admin.password)
    cursor.execute(
        """
        INSERT INTO admins (name, email, password, phone_number, date_of_birth, joining_date, national_id, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            admin.name,
            admin.email,
            hashed_pw,
            admin.phone_number,
            admin.date_of_birth,
            admin.joining_date,
            admin.national_id,
            admin.address,
        ),
    )

    admin_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "Admin registered successfully", "admin_id": admin_id}


@app.post("/admins/login")
def login_admin(credentials: UserLogin):
    """Admin login"""
    conn = get_db()
    cursor = conn.cursor()

    admin = cursor.execute(
        "SELECT * FROM admins WHERE email = ?",
        (credentials.email,),
    ).fetchone()

    if not admin:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    password_valid = bcrypt.checkpw(
        credentials.password.encode("utf-8"), admin["password"].encode("utf-8")
    )

    if not password_valid:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_token()
    cursor.execute(
        "UPDATE admins SET token = ? WHERE admin_id = ?", (token, admin["admin_id"])
    )
    conn.commit()
    conn.close()

    return {
        "message": "Admin login successful",
        "token": token,
        "admin_id": admin["admin_id"],
    }


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


@app.put("/admins/sellers/{seller_id}/approve")
def approve_seller(seller_id: int, current_admin: dict = Depends(get_current_admin)):
    """Approve a seller"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE sellers
        SET is_approved = 1, approved_by_admin_id = ?, approval_date = ?
        WHERE seller_id = ?
    """,
        (current_admin["admin_id"], date.today(), seller_id),
    )

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Seller not found")

    conn.commit()
    conn.close()

    return {"message": "Seller approved successfully"}


# --- Category Endpoints ---


@app.post("/categories")
def create_category(
    category: CategoryCreate, current_admin: dict = Depends(get_current_admin)
):
    """Create a new category (Admin only)"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if category name already exists
    existing_category = cursor.execute(
        "SELECT * FROM categories WHERE category_name = ?", (category.category_name,)
    ).fetchone()
    if existing_category:
        conn.close()
        raise HTTPException(status_code=400, detail="Category name already exists")

    cursor.execute(
        "INSERT INTO categories (category_name, image) VALUES (?, ?)",
        (category.category_name, category.image),
    )

    category_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "Category created", "category_id": category_id}


@app.put("/categories/{category_id}")
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_admin: dict = Depends(get_current_admin),
):
    """Update category details (Admin only)"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if category exists
    existing_category = cursor.execute(
        "SELECT * FROM categories WHERE category_id = ?", (category_id,)
    ).fetchone()

    if not existing_category:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if the new category name already exists (and is not the current one)
    if (
        category_update.category_name is not None
        and category_update.category_name != existing_category["category_name"]
    ):
        existing_with_new_name = cursor.execute(
            "SELECT * FROM categories WHERE category_name = ?",
            (category_update.category_name,),
        ).fetchone()
        if existing_with_new_name:
            conn.close()
            raise HTTPException(status_code=400, detail="Category name already exists")

    update_fields = []
    update_values = []

    if category_update.category_name is not None:
        update_fields.append("category_name = ?")
        update_values.append(category_update.category_name)
    if category_update.image is not None:
        update_fields.append("image = ?")
        update_values.append(category_update.image)

    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(update_fields)
    query = f"UPDATE categories SET {set_clause} WHERE category_id = ?"
    update_values.append(category_id)

    cursor.execute(query, tuple(update_values))
    conn.commit()
    conn.close()

    return {"message": "Category updated successfully", "category_id": category_id}


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, current_admin: dict = Depends(get_current_admin)):
    """Delete a category (Admin only), preventing deletion if products are associated with it."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if category exists
    existing_category = cursor.execute(
        "SELECT * FROM categories WHERE category_id = ?", (category_id,)
    ).fetchone()

    if not existing_category:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for associated products
    product_count = cursor.execute(
        "SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,)
    ).fetchone()[0]

    if product_count > 0:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category: products are associated with it. Please reassign or delete products first.",
        )

    cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
    conn.commit()
    conn.close()

    return {"message": "Category deleted successfully", "category_id": category_id}


@app.get("/categories")
def get_categories():
    """Get all categories"""
    conn = get_db()
    cursor = conn.cursor()

    categories = cursor.execute("SELECT * FROM categories").fetchall()
    conn.close()

    return [dict(cat) for cat in categories]


# --- Shop Endpoints ---


@app.post("/shops")
def create_shop(shop: ShopCreate, current_user: dict = Depends(get_current_user)):
    """Create a shop (Seller only)"""
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only sellers can create shops")

    conn = get_db()
    cursor = conn.cursor()

    # Get seller_id
    seller = cursor.execute(
        "SELECT seller_id, is_approved FROM sellers WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not seller or not seller["is_approved"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Seller must be approved by admin")

    # Check if seller already has a shop
    existing_shop = cursor.execute(
        "SELECT * FROM shops WHERE seller_id = ?", (seller["seller_id"],)
    ).fetchone()
    if existing_shop:
        conn.close()
        raise HTTPException(status_code=400, detail="Seller already has a shop.")

    cursor.execute(
        """
        INSERT INTO shops (seller_id, shop_name, description, address, contact_phone)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            seller["seller_id"],
            shop.shop_name,
            shop.description,
            shop.address,
            shop.contact_phone,
        ),
    )

    shop_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "Shop created successfully", "shop_id": shop_id}


@app.put("/shops/{shop_id}")
def update_shop(
    shop_id: int,
    shop_update: ShopCreate,  # Reusing ShopCreate for update fields
    current_user: dict = Depends(get_current_user),
):
    """Update shop details (Seller only)"""
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only sellers can update shops")

    conn = get_db()
    cursor = conn.cursor()

    # Verify shop ownership
    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?", (current_user["user_id"],)
    ).fetchone()

    if not seller:
        conn.close()
        raise HTTPException(status_code=403, detail="Seller not found")

    # Check if the shop belongs to the seller
    shop = cursor.execute(
        "SELECT * FROM shops WHERE shop_id = ? AND seller_id = ?",
        (shop_id, seller["seller_id"]),
    ).fetchone()

    if not shop:
        conn.close()
        raise HTTPException(
            status_code=404, detail="Shop not found or not owned by seller"
        )

    update_fields = []
    update_values = []

    if shop_update.shop_name is not None:
        update_fields.append("shop_name = ?")
        update_values.append(shop_update.shop_name)
    if shop_update.description is not None:
        update_fields.append("description = ?")
        update_values.append(shop_update.description)
    if shop_update.address is not None:
        update_fields.append("address = ?")
        update_values.append(shop_update.address)
    if shop_update.contact_phone is not None:
        update_fields.append("contact_phone = ?")
        update_values.append(shop_update.contact_phone)

    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(update_fields)
    query = f"UPDATE shops SET {set_clause} WHERE shop_id = ?"
    update_values.append(shop_id)

    cursor.execute(query, tuple(update_values))
    conn.commit()
    conn.close()

    return {"message": "Shop updated successfully", "shop_id": shop_id}


@app.get("/shops/my-shops")
def get_my_shops(current_user: dict = Depends(get_current_user)):
    """Get seller's shops"""
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only sellers can view their shops")

    conn = get_db()
    cursor = conn.cursor()

    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?", (current_user["user_id"],)
    ).fetchone()

    if not seller:
        conn.close()
        raise HTTPException(status_code=404, detail="Seller profile not found.")

    shops = cursor.execute(
        "SELECT * FROM shops WHERE seller_id = ?", (seller["seller_id"],)
    ).fetchall()

    conn.close()
    return [dict(shop) for shop in shops]


@app.get("/shops/all")  # Changed from get_all_shops to /shops/all for clarity
def get_all_shops():
    """Get all shops"""
    conn = get_db()
    cursor = conn.cursor()

    shops = cursor.execute("SELECT * FROM shops").fetchall()
    conn.close()

    return [dict(shop) for shop in shops]


@app.get("/shops/{shop_id}")
def get_shop_details(shop_id: int):
    """Get details of a specific shop"""
    conn = get_db()
    cursor = conn.cursor()

    shop = cursor.execute(
        "SELECT * FROM shops WHERE shop_id = ?", (shop_id,)
    ).fetchone()
    conn.close()

    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    return dict(shop)


# --- Product Endpoints ---


@app.post("/products")
def create_product(
    product: ProductCreate, current_user: dict = Depends(get_current_user)
):
    """Create a product (Seller only)"""
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only sellers can create products")

    conn = get_db()
    cursor = conn.cursor()

    # Verify shop ownership
    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?", (current_user["user_id"],)
    ).fetchone()

    if not seller:
        conn.close()
        raise HTTPException(status_code=403, detail="Seller profile not found.")

    shop = cursor.execute(
        "SELECT * FROM shops WHERE shop_id = ? AND seller_id = ?",
        (product.shop_id, seller["seller_id"]),
    ).fetchone()

    if not shop:
        conn.close()
        raise HTTPException(
            status_code=403, detail="Shop not found or not owned by seller"
        )

    # Verify category exists
    category = cursor.execute(
        "SELECT * FROM categories WHERE category_id = ?", (product.category_id,)
    ).fetchone()
    if not category:
        conn.close()
        raise HTTPException(status_code=404, detail="Category not found")

    cursor.execute(
        """
        INSERT INTO products (shop_id, category_id, product_name, description, image,
                            price, unit_price, stock_quantity, product_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            product.shop_id,
            product.category_id,
            product.product_name,
            product.description,
            product.image,
            product.price,
            product.unit_price,
            product.stock_quantity,
            product.product_status,
        ),
    )

    product_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"message": "Product created successfully", "product_id": product_id}


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a product (Seller only)"""
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only sellers can update products")

    conn = get_db()
    cursor = conn.cursor()

    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?", (current_user["user_id"],)
    ).fetchone()

    if not seller:
        conn.close()
        raise HTTPException(status_code=403, detail="Seller not found")

    # Check if the product exists and belongs to the seller's shop
    product = cursor.execute(
        "SELECT p.product_id, p.category_id, p.shop_id FROM products p JOIN shops s ON p.shop_id = s.shop_id WHERE p.product_id = ? AND s.seller_id = ?",
        (product_id, seller["seller_id"]),
    ).fetchone()

    if not product:
        conn.close()
        raise HTTPException(
            status_code=404, detail="Product not found or not owned by seller"
        )

    # Construct update query dynamically
    update_fields = []
    update_values = []

    if product_update.product_name is not None:
        update_fields.append("product_name = ?")
        update_values.append(product_update.product_name)
    if product_update.description is not None:
        update_fields.append("description = ?")
        update_values.append(product_update.description)
    if product_update.image is not None:
        update_fields.append("image = ?")
        update_values.append(product_update.image)
    if product_update.price is not None:
        update_fields.append("price = ?")
        update_values.append(product_update.price)
    if product_update.unit_price is not None:
        update_fields.append("unit_price = ?")
        update_values.append(product_update.unit_price)
    if product_update.stock_quantity is not None:
        update_fields.append("stock_quantity = ?")
        update_values.append(product_update.stock_quantity)
    if product_update.product_status is not None:
        update_fields.append("product_status = ?")
        update_values.append(product_update.product_status.value)

    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(update_fields)
    query = f"UPDATE products SET {set_clause} WHERE product_id = ?"
    update_values.append(product_id)

    cursor.execute(query, tuple(update_values))
    conn.commit()
    conn.close()

    return {"message": "Product updated successfully", "product_id": product_id}


@app.delete("/products/{product_id}")
def delete_product(product_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a product (Seller only), preventing deletion if it's the last product in its category."""
    if current_user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only sellers can delete products")

    conn = get_db()
    cursor = conn.cursor()

    seller = cursor.execute(
        "SELECT seller_id FROM sellers WHERE user_id = ?", (current_user["user_id"],)
    ).fetchone()

    if not seller:
        conn.close()
        raise HTTPException(status_code=403, detail="Seller not found")

    # Get product details and verify ownership
    product = cursor.execute(
        "SELECT p.product_id, p.category_id FROM products p JOIN shops s ON p.shop_id = s.shop_id WHERE p.product_id = ? AND s.seller_id = ?",
        (product_id, seller["seller_id"]),
    ).fetchone()

    if not product:
        conn.close()
        raise HTTPException(
            status_code=404, detail="Product not found or not owned by seller"
        )

    category_id = product["category_id"]

    # Check if this is the last product in its category
    product_count_in_category = cursor.execute(
        "SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,)
    ).fetchone()[0]

    if product_count_in_category == 1:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the last product in a category. Each category must have at least one product.",
        )

    # Before deleting, check for related order details to prevent orphaned data
    order_details_count = cursor.execute(
        "SELECT COUNT(*) FROM order_details WHERE product_id = ?", (product_id,)
    ).fetchone()[0]

    if order_details_count > 0:
        # Option 1: Prevent deletion and inform the user
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete product: it is part of existing orders. Please consider deactivating the product instead.",
        )
        # Option 2: Soft delete (e.g., update product_status to 'inactive' or 'discontinued')
        # This would require modifying the product schema and this endpoint logic.
        # For now, we enforce strict deletion prevention.

    # Also check for cart items
    cart_items_count = cursor.execute(
        "SELECT COUNT(*) FROM cart_items WHERE product_id = ?", (product_id,)
    ).fetchone()[0]
    if cart_items_count > 0:
        # Remove from cart if product is deleted
        cursor.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))

    cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

    return {"message": "Product deleted successfully", "product_id": product_id}


@app.get("/products")
def get_products(category_id: Optional[int] = None, shop_id: Optional[int] = None):
    """Browse all products with optional filters"""
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT p.*, s.shop_name FROM products p JOIN shops s ON p.shop_id = s.shop_id WHERE p.product_status = 'active'"
    params = []

    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    if shop_id:
        query += " AND p.shop_id = ?"
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
        "SELECT p.*, s.shop_name FROM products p JOIN shops s ON p.shop_id = s.shop_id WHERE p.product_id = ?",
        (product_id,),
    ).fetchone()
    conn.close()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return dict(product)


# --- Cart Endpoints ---


@app.post("/cart")
def add_to_cart(item: CartItemAdd, current_user: dict = Depends(get_current_user)):
    """Add product to cart"""
    if current_user["role"] != "customer":
        raise HTTPException(status_code=403, detail="Only customers can add to cart")

    conn = get_db()
    cursor = conn.cursor()

    # Get customer_id
    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer profile not found.")

    # Get product details (check if product exists and is active)
    product = cursor.execute(
        "SELECT price, stock_quantity, product_status FROM products WHERE product_id = ?",
        (item.product_id,),
    ).fetchone()

    if not product:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    if product["product_status"] != ProductStatus.ACTIVE.value:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Product is not available. Status: {product['product_status']}",
        )

    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive.")

    if item.quantity > product["stock_quantity"]:
        raise HTTPException(
            status_code=400,
            detail=f"Requested quantity ({item.quantity}) exceeds available stock ({product['stock_quantity']}).",
        )

    # Check if item already exists in cart, if so, update quantity
    existing_cart_item = cursor.execute(
        "SELECT * FROM cart_items WHERE customer_id = ? AND product_id = ?",
        (customer["customer_id"], item.product_id),
    ).fetchone()

    if existing_cart_item:
        new_quantity = existing_cart_item["quantity"] + item.quantity
        if new_quantity > product["stock_quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Requested quantity ({new_quantity}) exceeds available stock ({product['stock_quantity']}).",
            )
        cursor.execute(
            "UPDATE cart_items SET quantity = ? WHERE cart_item_id = ?",
            (new_quantity, existing_cart_item["cart_item_id"]),
        )
    else:
        cursor.execute(
            """
            INSERT INTO cart_items (customer_id, product_id, quantity, price_at_addition)
            VALUES (?, ?, ?, ?)
        """,
            (customer["customer_id"], item.product_id, item.quantity, product["price"]),
        )

    conn.commit()
    conn.close()

    return {"message": "Product added to cart"}


@app.get("/cart")
def get_cart(current_user: dict = Depends(get_current_user)):
    """Get customer's cart"""
    if current_user["role"] != "customer":
        raise HTTPException(status_code=403, detail="Only customers have carts")

    conn = get_db()
    cursor = conn.cursor()

    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer profile not found.")

    cart_items = cursor.execute(
        """
        SELECT ci.cart_item_id, ci.product_id, p.product_name, p.image, ci.quantity, ci.price_at_addition, (ci.quantity * ci.price_at_addition) as subtotal
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.product_id
        WHERE ci.customer_id = ?
    """,
        (customer["customer_id"],),
    ).fetchall()
    conn.close()

    return [dict(item) for item in cart_items]


@app.delete("/cart/{cart_item_id}")
def remove_from_cart(cart_item_id: int, current_user: dict = Depends(get_current_user)):
    """Remove item from cart"""
    conn = get_db()
    cursor = conn.cursor()

    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer profile not found.")

    # Check if cart item belongs to the customer
    cart_item = cursor.execute(
        "SELECT * FROM cart_items WHERE cart_item_id = ? AND customer_id = ?",
        (cart_item_id, customer["customer_id"]),
    ).fetchone()

    if not cart_item:
        conn.close()
        raise HTTPException(
            status_code=404, detail="Cart item not found or does not belong to you."
        )

    cursor.execute("DELETE FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
    conn.commit()
    conn.close()

    return {"message": "Item removed from cart"}


# --- Order Endpoints ---


@app.post("/checkout")
def checkout(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    """Checkout and create order from cart"""
    if current_user["role"] != "customer":
        raise HTTPException(status_code=403, detail="Only customers can place orders")

    conn = get_db()
    cursor = conn.cursor()

    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer profile not found.")

    # Get cart items and validate stock before proceeding
    cart_items = cursor.execute(
        """
        SELECT ci.cart_item_id, ci.product_id, ci.quantity, ci.price_at_addition, p.stock_quantity, p.product_status
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.product_id
        WHERE ci.customer_id = ?
    """,
        (customer["customer_id"],),
    ).fetchall()

    if not cart_items:
        conn.close()
        raise HTTPException(status_code=400, detail="Cart is empty")

    total_amount = 0
    products_to_update_stock = []

    for item in cart_items:
        if item["product_status"] != ProductStatus.ACTIVE.value:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Product '{item['product_id']}' is not available.",
            )
        if item["quantity"] > item["stock_quantity"]:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Product '{item['product_id']}' has insufficient stock. Requested: {item['quantity']}, Available: {item['stock_quantity']}.",
            )

        subtotal = item["price_at_addition"] * item["quantity"]
        total_amount += subtotal
        products_to_update_stock.append(
            {
                "product_id": item["product_id"],
                "quantity_ordered": item["quantity"],
                "new_stock_quantity": item["stock_quantity"] - item["quantity"],
            }
        )

    # Create order
    cursor.execute(
        """
        INSERT INTO orders (customer_id, total_amount, shipping_address)
        VALUES (?, ?, ?)
    """,
        (customer["customer_id"], total_amount, order_data.shipping_address),
    )

    order_id = cursor.lastrowid

    # Create order details and update stock
    for item in cart_items:
        subtotal = item["price_at_addition"] * item["quantity"]
        cursor.execute(
            """
            INSERT INTO order_details (order_id, product_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                order_id,
                item["product_id"],
                item["quantity"],
                item["price_at_addition"],
                subtotal,
            ),
        )

    for update_info in products_to_update_stock:
        cursor.execute(
            "UPDATE products SET stock_quantity = ? WHERE product_id = ?",
            (update_info["new_stock_quantity"], update_info["product_id"]),
        )
        # Update product status if stock reaches zero
        if update_info["new_stock_quantity"] == 0:
            cursor.execute(
                "UPDATE products SET product_status = ? WHERE product_id = ?",
                (ProductStatus.OUT_OF_STOCK.value, update_info["product_id"]),
            )

    # Create payment
    transaction_id = f"TXN{secrets.token_hex(8).upper()}"
    cursor.execute(
        """
        INSERT INTO payments (order_id, customer_id, amount, payment_method, transaction_id, transaction_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            order_id,
            customer["customer_id"],
            total_amount,
            order_data.payment_method,
            transaction_id,
            PaymentStatus.COMPLETED.value,
        ),
    )  # Assuming payment is completed upon checkout

    # Create shipment
    tracking_number = f"TRACK{secrets.token_hex(6).upper()}"
    cursor.execute(
        """
        INSERT INTO shipments (order_id, shipping_address, tracking_number)
        VALUES (?, ?, ?)
    """,
        (order_id, order_data.shipping_address, tracking_number),
    )

    # Clear cart
    cursor.execute(
        "DELETE FROM cart_items WHERE customer_id = ?", (customer["customer_id"],)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Order placed successfully",
        "order_id": order_id,
        "transaction_id": transaction_id,
        "tracking_number": tracking_number,
    }


@app.get("/orders/my")  # Changed from get_my_orders to /orders/my
def get_my_orders(current_user: dict = Depends(get_current_user)):
    """Get customer's orders"""
    if current_user["role"] != "customer":
        raise HTTPException(status_code=403, detail="Only customers have orders")

    conn = get_db()
    cursor = conn.cursor()

    customer = cursor.execute(
        "SELECT customer_id FROM customers WHERE user_id = ?",
        (current_user["user_id"],),
    ).fetchone()

    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer profile not found.")

    orders = cursor.execute(
        """
        SELECT o.order_id, o.order_date, o.total_amount, o.payment_status, o.delivery_status,
               p.transaction_id, s.tracking_number
        FROM orders o
        LEFT JOIN payments p ON o.order_id = p.order_id
        LEFT JOIN shipments s ON o.order_id = s.order_id
        WHERE o.customer_id = ?
        ORDER BY o.order_date DESC
    """,
        (customer["customer_id"],),
    ).fetchall()
    conn.close()

    return [dict(order) for order in orders]


@app.get("/orders/{order_id}")
def get_order_details(order_id: int, current_user: dict = Depends(get_current_user)):
    """Get order details"""
    conn = get_db()
    cursor = conn.cursor()

    # Fetch order and check if it belongs to the current user
    order = cursor.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()

    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    # Ensure the order belongs to the current customer
    if (
        order["customer_id"] != current_user["customer_id"]
    ):  # This assumes current_user dict has 'customer_id' if role is customer
        # Need to fetch customer_id if not directly available in current_user or add it to get_current_user logic
        customer_check = cursor.execute(
            "SELECT customer_id FROM customers WHERE user_id = ?",
            (current_user["user_id"],),
        ).fetchone()
        if not customer_check or order["customer_id"] != customer_check["customer_id"]:
            conn.close()
            raise HTTPException(
                status_code=403, detail="You can only view your own orders."
            )
        # If it belongs to the customer, we can proceed.

    order_items = cursor.execute(
        """
        SELECT od.order_detail_id, od.product_id, p.product_name, p.image, od.quantity, od.unit_price, od.discount, od.subtotal
        FROM order_details od
        JOIN products p ON od.product_id = p.product_id
        WHERE od.order_id = ?
    """,
        (order_id,),
    ).fetchall()

    payment = cursor.execute(
        "SELECT * FROM payments WHERE order_id = ?", (order_id,)
    ).fetchone()

    shipment = cursor.execute(
        "SELECT * FROM shipments WHERE order_id = ?", (order_id,)
    ).fetchone()

    conn.close()

    return {
        "order": dict(order),
        "items": [dict(item) for item in order_items],
        "payment": dict(payment) if payment else None,
        "shipment": dict(shipment) if shipment else None,
    }


# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the E-commerce API!"}
