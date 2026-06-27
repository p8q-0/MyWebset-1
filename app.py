from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from logging.config import dictConfig
from pathlib import Path
from typing import Any
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "MyWebset_data"
DATABASE_PATH = DATA_DIR / "database.sqlite"  # <--- أضف هذا السطر هنا
import os
import psycopg2
from psycopg2.extras import DictCursor

# جلب الرابط وإجبار السيرفر على قراءته من البيئة (Environment)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", str(DATA_DIR / "uploads" / "products")))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
SESSION_ADMIN_KEY = "admin_id"
SESSION_CSRF_KEY = "admin_csrf"
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en": "English", "ar": "العربية"}
TRANSLATIONS = {
    "lumora_cosmetics": {"en": "Lumora Cosmetics", "ar": "لومورا كوزميتكس"},
    "home": {"en": "Home", "ar": "الرئيسية"},
    "shop": {"en": "Shop", "ar": "المتجر"},
    "cart": {"en": "Cart", "ar": "السلة"},
    "checkout": {"en": "Checkout", "ar": "الدفع"},
    "featured_products": {"en": "Featured Products", "ar": "المنتجات المميزة"},
    "filter_by_category": {"en": "Filter by category", "ar": "تصفية حسب الفئة"},
    "all_products": {"en": "All products", "ar": "جميع المنتجات"},
    "luxury_beauty_reimagined": {"en": "Luxury beauty, reimagined", "ar": "الجمال الفاخر بشكل جديد"},
    "reveal_your_natural_beauty": {"en": "Reveal Your Natural Beauty", "ar": "أظهر جمالك الطبيعي"},
    "discover_luxury": {"en": "Discover luxurious skincare and cosmetics crafted to enhance your glow with a soft, modern finish that feels effortlessly premium.", "ar": "اكتشفي مستحضرات العناية بالبشرة والمكياج الفاخرة المصممة لتعزيز إشراقتك بأسلوب ناعم وعصري."},
    "shop_now": {"en": "Shop Now", "ar": "تسوق الآن"},
    "explore_collection": {"en": "Explore Collection", "ar": "استكشف المجموعة"},
    "dermatologist_loved_formulas": {"en": "Dermatologist-loved formulas", "ar": "تركيبات محبوبة من أطباء الجلد"},
    "velvety_finishes": {"en": "Velvety finishes", "ar": "لمسات مخملية"},
    "free_shipping": {"en": "Free shipping over $50", "ar": "شحن مجاني للطلبات فوق 50$"},
    "beauty_with_calm_luxury": {"en": "Beauty with calm luxury", "ar": "جمال برفاهية هادئة"},
    "no_products_found": {"en": "No products found", "ar": "لم يتم العثور على منتجات"},
    "no_products_in_category": {"en": "No products in the {category} category.", "ar": "لا توجد منتجات في فئة {category}."},
    "populate_storefront": {"en": "Add products to populate the storefront.", "ar": "أضف منتجات لعرضها في المتجر."},
    "unable_to_load_products": {"en": "Unable to load products", "ar": "غير قادر على تحميل المنتجات"},
    "item_added_to_cart": {"en": "added to cart", "ar": "أضيف إلى السلة"},
    "item_removed_from_cart": {"en": "Item removed from cart", "ar": "تمت إزالة العنصر من السلة"},
    "your_cart_is_empty": {"en": "Your cart is empty", "ar": "سلتك فارغة"},
    "add_items_to_begin": {"en": "Add a few items from the storefront to begin.", "ar": "أضف بعض المنتجات من المتجر للبدء."},
    "continue_shopping": {"en": "Continue shopping", "ar": "تابع التسوق"},
    "order_summary": {"en": "Order summary", "ar": "ملخص الطلب"},
    "items": {"en": "Items", "ar": "العناصر"},
    "total": {"en": "Total", "ar": "الإجمالي"},
    "checkout_via_whatsapp": {"en": "Checkout via WhatsApp", "ar": "الدفع عبر واتساب"},
    "need_help_choosing": {"en": "Need help choosing?", "ar": "تحتاج مساعدة في الاختيار؟"},
    "help_build_routine": {"en": "Our team can help you build your perfect routine in minutes.", "ar": "فريقنا يمكنه مساعدتك في بناء روتينك المثالي خلال دقائق."},
    "fast_and_secure": {"en": "Fast and secure", "ar": "سريع وآمن"},
    "whatsapp_order_info": {"en": "Your order opens in WhatsApp instantly so you can review and send it without friction.", "ar": "يتم فتح طلبك في واتساب فوراً حتى تتمكن من مراجعته وإرساله بسهولة."},
    "no_order_storage": {"en": "No order storage", "ar": "لا يتم حفظ الطلب"},
    "name": {"en": "Name", "ar": "الاسم"},
    "phone": {"en": "Phone", "ar": "الهاتف"},
    "address": {"en": "Address", "ar": "العنوان"},
    "notes": {"en": "Notes", "ar": "ملاحظات"},
    "confirm_order": {"en": "Confirm order", "ar": "تأكيد الطلب"},
    "loading_category": {"en": "Loading category", "ar": "جارٍ تحميل الفئة"},
    "loading_product": {"en": "Loading product...", "ar": "جارٍ تحميل المنتج..."},
    "fetching_product_data": {"en": "Fetching product data from the API.", "ar": "جارٍ جلب بيانات المنتج من الخادم."},
    "in_stock": {"en": "In stock", "ar": "متوفر"},
    "add_to_cart": {"en": "Add to cart", "ar": "أضف إلى السلة"},
    "view_cart": {"en": "View cart", "ar": "عرض السلة"},
    "luxury_finish": {"en": "Luxury finish", "ar": "لمسة فاخرة"},
    "fast_delivery": {"en": "Fast delivery", "ar": "توصيل سريع"},
    "soft_glow": {"en": "Soft glow and refined texture for everyday wear.", "ar": "لمعان ناعم وملمس مصقول للارتداء اليومي."},
    "admin_access": {"en": "Admin access", "ar": "وصول الإدارة"},
    "sign_in_dashboard": {"en": "Sign in to the dashboard", "ar": "تسجيل الدخول للوحة التحكم"},
    "username": {"en": "Username", "ar": "اسم المستخدم"},
    "password": {"en": "Password", "ar": "كلمة المرور"},
    "log_in": {"en": "Log in", "ar": "تسجيل الدخول"},
    "default_credentials_note": {"en": "Default credentials are seeded in SQLite on first launch and should be changed for production.", "ar": "بيانات الدخول الافتراضية تُنشأ في SQLite عند التشغيل الأول ويجب تغييرها في بيئة الإنتاج."},
}
PRODUCT_CATEGORIES = ["Lips", "Face", "Eyes", "Skin"]

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.before_request
def initialize_app_on_first_request():
    # هذا السطر يضمن أن قاعدة البيانات ستُهيأ مرة واحدة فقط عند أول زيارة للموقع
    app.before_request_funcs[None].remove(initialize_app_on_first_request)
    init_db()

def init_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": "INFO",
                }
            },
            "root": {"level": "INFO", "handlers": ["console"]},
        }
    )

disable_rate_limiting = os.environ.get("DISABLE_RATE_LIMITING", "false").lower() in ("1", "true", "yes")
limiter = Limiter(key_func=get_remote_address, default_limits=[], enabled=not disable_rate_limiting)


def configure_app(application: Flask) -> None:
    secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    application.config.update(
        SECRET_KEY=secret_key,
        UPLOAD_FOLDER=str(UPLOAD_FOLDER),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PREFERRED_URL_SCHEME="https",
        FORCE_HTTPS=os.environ.get("FORCE_HTTPS", "false").lower() in ("1", "true", "yes"),
        DISABLE_RATE_LIMITING=disable_rate_limiting,
    )
    init_logging()
    application.wsgi_app = ProxyFix(application.wsgi_app, x_proto=1, x_host=1)
    limiter.init_app(application)


configure_app(app)


def get_db():
    import psycopg2
    from psycopg2.extras import DictCursor

    if 'db' not in g:
        if os.environ.get("DATABASE_URL"):
            g.db = psycopg2.connect(os.environ.get("DATABASE_URL"), cursor_factory=DictCursor)
        else:
            g.db = sqlite3.connect(DATABASE_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db

def bootstrap_admin_from_env(db: sqlite3.Connection) -> None:
    username = os.environ.get("INITIAL_ADMIN_USERNAME")
    password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    if username and password:
        username = str(username).strip()
        password = str(password)
        if username and password:
            db.execute(
                "INSERT INTO admins (id, username, password) VALUES (?, ?, ?)",
                (1, username, generate_password_hash(password)),
            )
            app.logger.info("Initial admin account created from environment variables")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    # استيراد الدالة محلياً داخل الدالة لضمان أن البايثون يراها بدون مشاكل
    from werkzeug.security import generate_password_hash

    with get_db() as db:
        cursor = db.cursor()
        
        # إنشاء الجداول بصيغة Postgres إذا كنا على سيرفر Railway
        if DATABASE_URL:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL,
                    category TEXT NOT NULL,
                    stock INTEGER NOT NULL DEFAULT 0,
                    image TEXT NOT NULL DEFAULT ''
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)
        else:
            # لقواعد SQLite المحلية إذا كنت تجرب على جهازك
            cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL, price REAL NOT NULL, category TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 0, image TEXT NOT NULL DEFAULT '')")
            cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")

        # مراجعة وإنشاء حساب الأدمن الافتراضي
        cursor.execute("SELECT id FROM admins LIMIT 1")
        existing_admin = cursor.fetchone()
        if existing_admin is None:
            username = os.environ.get("INITIAL_ADMIN_USERNAME", "admin").strip()
            password = os.environ.get("INITIAL_ADMIN_PASSWORD", "admin123")
            param_char = "%s" if DATABASE_URL else "?"
            cursor.execute(f"INSERT INTO admins (username, password) VALUES ({param_char}, {param_char})", (username, generate_password_hash(password)))
            app.logger.info("Initial admin account created")

        # مراجعة وإنشاء المنتجات الافتراضية
        cursor.execute("SELECT COUNT(*) FROM products")
        if DATABASE_URL:
            existing_products = cursor.fetchone()[0]
        else:
            existing_products = cursor.fetchone()[0]

        if existing_products == 0:
            param_char = "%s" if DATABASE_URL else "?"
            cursor.executemany(
                f"INSERT INTO products (name, description, price, category, stock, image) VALUES ({param_char}, {param_char}, {param_char}, {param_char}, {param_char}, {param_char})",
                [
                    ("Velvet Rose Lipstick", "Creamy long-wear lipstick with a soft matte finish.", 24.0, "Lips", 42, "/static/images/placeholder.svg"),
                    ("Glow Silk Foundation", "Lightweight buildable foundation with a radiant finish.", 38.0, "Face", 28, "/static/images/placeholder.svg"),
                    ("Moonlit Lash Mascara", "Lengthening mascara for defined, lifted lashes.", 21.5, "Eyes", 35, "/static/images/placeholder.svg"),
                    ("Aurora Hydration Serum", "Daily serum that helps skin feel plump and luminous.", 31.0, "Skin", 20, "/static/images/placeholder.svg"),
                ],
            )

        # مراجعة الفئات
        cursor.execute("SELECT COUNT(*) FROM categories")
        existing_categories = cursor.fetchone()[0]
        if existing_categories == 0:
            param_char = "%s" if DATABASE_URL else "?"
            cursor.executemany(
                f"INSERT INTO categories (name) VALUES ({param_char})",
                [(name,) for name in PRODUCT_CATEGORIES],
            )
        db.commit()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    with get_db() as db:
        cursor = db.cursor()
        
        # إنشاء الجداول بصيغة Postgres
        if DATABASE_URL:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL,
                    category TEXT NOT NULL,
                    stock INTEGER NOT NULL DEFAULT 0,
                    image TEXT NOT NULL DEFAULT ''
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)
        else:
            # ديا لقواعد SQLite القديمة لو شغال لوكال
            cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL, price REAL NOT NULL, category TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 0, image TEXT NOT NULL DEFAULT '')")
            cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")

        # مراجعة وجود الأدمن
        cursor.execute("SELECT id FROM admins LIMIT 1")
        existing_admin = cursor.fetchone()
        if existing_admin is None:
            # هنا بنمرر الـ db والـ cursor عشان يشتغلوا مع psycopg2
            username = os.environ.get("INITIAL_ADMIN_USERNAME", "admin").strip()
            password = os.environ.get("INITIAL_ADMIN_PASSWORD", "admin123")
            param_char = "%s" if DATABASE_URL else "?"
            cursor.execute(f"INSERT INTO admins (username, password) VALUES ({param_char}, {param_char})", (username, generate_password_hash(password)))
            app.logger.info("Initial admin account created")

        # مراجعة المنتجات
        cursor.execute("SELECT COUNT(*) FROM products")
        existing_products = cursor.fetchone()[0]
        if existing_products == 0:
            param_char = "%s" if DATABASE_URL else "?"
            cursor.executemany(
                f"INSERT INTO products (name, description, price, category, stock, image) VALUES ({param_char}, {param_char}, {param_char}, {param_char}, {param_char}, {param_char})",
                [
                    ("Velvet Rose Lipstick", "Creamy long-wear lipstick with a soft matte finish.", 24.0, "Lips", 42, "/static/images/placeholder.svg"),
                    ("Glow Silk Foundation", "Lightweight buildable foundation with a radiant finish.", 38.0, "Face", 28, "/static/images/placeholder.svg"),
                    ("Moonlit Lash Mascara", "Lengthening mascara for defined, lifted lashes.", 21.5, "Eyes", 35, "/static/images/placeholder.svg"),
                    ("Aurora Hydration Serum", "Daily serum that helps skin feel plump and luminous.", 31.0, "Skin", 20, "/static/images/placeholder.svg"),
                ],
            )

        # مراجعة الفئات
        cursor.execute("SELECT COUNT(*) FROM categories")
        existing_categories = cursor.fetchone()[0]
        if existing_categories == 0:
            param_char = "%s" if DATABASE_URL else "?"
            cursor.executemany(
                f"INSERT INTO categories (name) VALUES ({param_char})",
                [(name,) for name in PRODUCT_CATEGORIES],
            )
        db.commit()
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                image TEXT NOT NULL DEFAULT ''
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """
        )
        existing_admin = db.execute("SELECT id FROM admins LIMIT 1").fetchone()
        if existing_admin is None:
            bootstrap_admin_from_env(db)
            existing_admin = db.execute("SELECT id FROM admins LIMIT 1").fetchone()
            if existing_admin is None:
                raise RuntimeError(
                    "No admin account exists. Set INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD before startup."
                )
        existing_products = db.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
        if existing_products == 0:
            db.executemany(
                "INSERT INTO products (name, description, price, category, stock, image) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        "Velvet Rose Lipstick",
                        "Creamy long-wear lipstick with a soft matte finish.",
                        24.0,
                        "Lips",
                        42,
                        "/static/images/placeholder.svg",
                    ),
                    (
                        "Glow Silk Foundation",
                        "Lightweight buildable foundation with a radiant finish.",
                        38.0,
                        "Face",
                        28,
                        "/static/images/placeholder.svg",
                    ),
                    (
                        "Moonlit Lash Mascara",
                        "Lengthening mascara for defined, lifted lashes.",
                        21.5,
                        "Eyes",
                        35,
                        "/static/images/placeholder.svg",
                    ),
                    (
                        "Aurora Hydration Serum",
                        "Daily serum that helps skin feel plump and luminous.",
                        31.0,
                        "Skin",
                        20,
                        "/static/images/placeholder.svg",
                    ),
                ],
            )
        existing_categories = db.execute("SELECT COUNT(*) AS count FROM categories").fetchone()["count"]
        if existing_categories == 0:
            db.executemany(
                "INSERT INTO categories (name) VALUES (?)",
                [(name,) for name in PRODUCT_CATEGORIES],
            )
        db.commit()


def resolve_language() -> str:
    requested = request.args.get("lang", "").lower()
    if requested in SUPPORTED_LANGUAGES:
        return requested
    saved = session.get("lang")
    if saved in SUPPORTED_LANGUAGES:
        return saved
    return DEFAULT_LANGUAGE


@app.before_request
def prepare_request() -> None:
    lang = resolve_language()
    if request.args.get("lang", "").lower() in SUPPORTED_LANGUAGES:
        session["lang"] = lang
    g.lang = lang

    if app.config.get("FORCE_HTTPS") and request.method in ("GET", "HEAD"):
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        if forwarded_proto != "https" and request.scheme != "https":
            return redirect(request.url.replace("http://", "https://"), code=301)


with app.app_context():
    init_db()


@app.after_request
def after_request(response):
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https://*; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none';"
    if app.config.get("FORCE_HTTPS"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
def disable_api_caching(response):
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "price": float(row["price"]),
        "category": row["category"],
        "stock": int(row["stock"]),
        "image": row["image"],
    }


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_int(value: Any, minimum: int | None = None) -> int:
    number = int(value)
    if minimum is not None and number < minimum:
        raise ValueError
    return number


def sanitize_float(value: Any, minimum: float | None = None) -> float:
    number = float(value)
    if minimum is not None and number < minimum:
        raise ValueError
    return number


def normalize_text(value: Any, max_length: int = 500) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError
    if len(text) > max_length:
        raise ValueError
    if "<" in text or ">" in text:
        raise ValueError
    return text


def validate_category(value: Any) -> str:
    category = normalize_text(value, 80)
    with get_db() as db:
        if db.execute("SELECT name FROM categories WHERE name = %s", (category,)).fetchone() is None:
            raise ValueError
    return category


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if SESSION_ADMIN_KEY not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("admin_login_page"))
        return view(*args, **kwargs)

    return wrapped


def csrf_protected() -> bool:
    token = session.get(SESSION_CSRF_KEY)
    header = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    return bool(token and header and secrets.compare_digest(token, header))


def require_csrf() -> None:
    if not csrf_protected():
        abort(403)


def current_admin() -> dict[str, Any] | None:
    admin_id = session.get(SESSION_ADMIN_KEY)
    if not admin_id:
        return None
    with get_db() as db:
        row = db.execute("SELECT id, username FROM admins WHERE id = %s", (admin_id,)).fetchone()
        if row is None:
            return None
        return {"id": row["id"], "username": row["username"]}


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/product/<int:product_id>")
def product_page(product_id: int) -> str:
    return render_template("product.html", product_id=product_id)


@app.route("/cart")
def cart_page() -> str:
    return render_template("cart.html")


@app.route("/checkout")
def checkout_page() -> str:
    return render_template("checkout.html")


@app.route("/admin-login")
def admin_login_page() -> str:
    if SESSION_ADMIN_KEY in session:
        return redirect(url_for("admin_dashboard_page"))
    return render_template("admin-login.html")


@app.route("/admin-dashboard")
@login_required
def admin_dashboard_page() -> str:
    admin = current_admin()
    return render_template("admin-dashboard.html", admin=admin, csrf_token=session.get(SESSION_CSRF_KEY))


@app.route("/uploads/products/<path:filename>")
def uploaded_product_image(filename: str):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/categories", methods=["GET"])
def api_get_categories():
    with get_db() as db:
        rows = db.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()
    return jsonify([row["name"] for row in rows])


@app.route("/api/categories", methods=["POST"])
@login_required
def api_create_category():
    require_csrf()
    payload = request.get_json(silent=True) or request.form
    try:
        name = normalize_text(payload.get("name"), 80)
    except (TypeError, ValueError):
        app.logger.warning("Invalid category creation payload")
        return jsonify({"error": "invalid category data"}), 400

    with get_db() as db:
        try:
            cursor = db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            db.commit()
            row = db.execute("SELECT name FROM categories WHERE id = %s", (cursor.lastrowid,)).fetchone()
        except sqlite3.IntegrityError:
            app.logger.warning("Duplicate category creation attempt: %s", name)
            return jsonify({"error": "category already exists"}), 409
    app.logger.info("Created category: %s", name)
    return jsonify({"name": row["name"]}), 201


@app.route("/api/categories/<path:category_name>", methods=["DELETE"])
@login_required
def api_delete_category(category_name: str):
    require_csrf()
    with get_db() as db:
        if db.execute("SELECT id FROM products WHERE category = %s", (category_name,)).fetchone() is not None:
            return jsonify({"error": "category is in use"}), 409
        db.execute("DELETE FROM categories WHERE name = %s", (category_name,))
        db.commit()
    app.logger.info("Deleted category: %s", category_name)
    return jsonify({"message": "deleted"})


@app.route("/api/products", methods=["GET"])
def api_get_products():
    with get_db() as db:
        rows = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return jsonify([row_to_product(row) for row in rows])


@app.route("/api/products/<int:product_id>", methods=["GET"])
def api_get_product(product_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(row_to_product(row))


@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
def api_login():
    payload = request.get_json(silent=True) or request.form
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        app.logger.warning("Login attempt with missing credentials")
        return jsonify({"error": "username and password are required"}), 400

    with get_db() as db:
        row = db.execute("SELECT * FROM admins WHERE username = %s", (username,)).fetchone()

    if row is None or not check_password_hash(row["password"], password):
        app.logger.warning("Failed login attempt for user: %s", username)
        return jsonify({"error": "invalid credentials"}), 401

    session.clear()
    session[SESSION_ADMIN_KEY] = row["id"]
    session[SESSION_CSRF_KEY] = secrets.token_urlsafe(32)
    app.logger.info("Admin logged in: %s", username)
    return jsonify({"message": "logged in", "admin": {"id": row["id"], "username": row["username"]}, "csrfToken": session[SESSION_CSRF_KEY]})


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    require_csrf()
    admin = current_admin()
    session.clear()
    app.logger.info("Admin logged out: %s", admin["username"] if admin else "unknown")
    return jsonify({"message": "logged out"})


@app.route("/api/session", methods=["GET"])
@login_required
def api_session():
    admin = current_admin()
    return jsonify({"authenticated": True, "admin": admin, "csrfToken": session.get(SESSION_CSRF_KEY)})


@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    require_csrf()
    if "image" not in request.files:
        app.logger.warning("Upload attempt without image file")
        return jsonify({"error": "image file required"}), 400
    file = request.files["image"]
    if not file.filename:
        app.logger.warning("Upload attempt with empty filename")
        return jsonify({"error": "image file required"}), 400
    if not allowed_file(file.filename):
        app.logger.warning("Unsupported upload file type: %s", file.filename)
        return jsonify({"error": "unsupported file type"}), 400

    filename = secure_filename(file.filename)
    unique_prefix = secrets.token_hex(8)
    final_name = f"{unique_prefix}_{filename}"
    save_path = UPLOAD_FOLDER / final_name
    file.save(save_path)
    app.logger.info("Uploaded product image: %s", final_name)
    return jsonify({"message": "uploaded", "filename": final_name, "url": url_for("uploaded_product_image", filename=final_name)})


@app.route("/api/products", methods=["POST"])
@login_required
def api_create_product():
    require_csrf()
    payload = request.get_json(silent=True) or request.form
    try:
        name = normalize_text(payload.get("name"), 120)
        description = normalize_text(payload.get("description"), 1000)
        category = validate_category(payload.get("category"))
        price = sanitize_float(payload.get("price"), 0)
        stock = sanitize_int(payload.get("stock"), 0)
        image = str(payload.get("image", "")).strip()
    except (TypeError, ValueError):
        app.logger.warning("Invalid product creation payload")
        return jsonify({"error": "invalid product data"}), 400

    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO products (name, description, price, category, stock, image) VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, price, category, stock, image),
        )
        db.commit()
        row = db.execute("SELECT * FROM products WHERE id = %s", (cursor.lastrowid,)).fetchone()
    app.logger.info("Created product: %s", name)
    return jsonify(row_to_product(row)), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@login_required
def api_update_product(product_id: int):
    require_csrf()
    payload = request.get_json(silent=True) or request.form
    with get_db() as db:
        existing = db.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "not found"}), 404

        try:
            name = normalize_text(payload.get("name", existing["name"]), 120)
            description = normalize_text(payload.get("description", existing["description"]), 1000)
            category = validate_category(payload.get("category", existing["category"]))
            price = sanitize_float(payload.get("price", existing["price"]), 0)
            stock = sanitize_int(payload.get("stock", existing["stock"]), 0)
            image = str(payload.get("image", existing["image"]) or "").strip()
        except (TypeError, ValueError):
            app.logger.warning("Invalid product update payload for id %s", product_id)
            return jsonify({"error": "invalid product data"}), 400

        db.execute(
            """
            UPDATE products
            SET name = ?, description = ?, price = ?, category = ?, stock = ?, image = ?
            WHERE id = ?
            """,
            (name, description, price, category, stock, image, product_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
    app.logger.info("Updated product %s: %s", product_id, name)
    return jsonify(row_to_product(row))


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@login_required
def api_delete_product(product_id: int):
    require_csrf()
    with get_db() as db:
        existing = db.execute("SELECT id FROM products WHERE id = %s", (product_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "not found"}), 404
        db.execute("DELETE FROM products WHERE id = %s", (product_id,))
        db.commit()
    app.logger.info("Deleted product id %s", product_id)
    return jsonify({"message": "deleted"})


@app.errorhandler(404)
def handle_404(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found"}), 404
    return redirect(url_for("index"))


@app.errorhandler(413)
def handle_413(_error):
    app.logger.warning("Request rejected: file too large")
    return jsonify({"error": "file too large"}), 413


@app.errorhandler(Exception)
def handle_unhandled_exception(error):
    from werkzeug.exceptions import HTTPException

    if isinstance(error, HTTPException):
        return error

    app.logger.exception("Unhandled exception")
    if request.path.startswith("/api/"):
        return jsonify({"error": "internal server error"}), 500
    return redirect(url_for("index"))


def translate(key: str, **kwargs: Any) -> str:
    text = TRANSLATIONS.get(key, {}).get(getattr(g, "lang", DEFAULT_LANGUAGE), TRANSLATIONS.get(key, {}).get(DEFAULT_LANGUAGE, key))
    if not kwargs:
        return text
    return text.format(**kwargs)


def build_lang_url(target_lang: str) -> str:
    if request.endpoint is None:
        return url_for("index", lang=target_lang)
    args = dict(request.view_args or {})
    query_args = request.args.to_dict(flat=True)
    query_args.pop("lang", None)
    args.update(query_args)
    args["lang"] = target_lang
    try:
        return url_for(request.endpoint, **args)
    except Exception:
        return url_for("index", lang=target_lang)


@app.context_processor
def inject_globals():
    with get_db() as db:
        categories = [row["name"] for row in db.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()]
    i18n_json = json.dumps(TRANSLATIONS, ensure_ascii=False)
    lang = getattr(g, "lang", DEFAULT_LANGUAGE)
    return {
        "logged_in_admin": current_admin(),
        "product_categories": categories,
        "t": translate,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
        "supported_languages": list(SUPPORTED_LANGUAGES.items()),
        "lang_url": build_lang_url,
        "i18n_json": i18n_json,
    }


if __name__ == "__main__":
    app.run(debug=True)