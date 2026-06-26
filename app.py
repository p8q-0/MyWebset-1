from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database.db"
UPLOAD_FOLDER = BASE_DIR / "uploads" / "products"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
SESSION_ADMIN_KEY = "admin_id"
SESSION_CSRF_KEY = "admin_csrf"
PRODUCT_CATEGORIES = ["Lips", "Face", "Eyes", "Skin"]

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cosmetics-store-dev-secret")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
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
        existing_admin = db.execute("SELECT id FROM admins WHERE username = ?", ("admin",)).fetchone()
        if existing_admin is None:
            db.execute(
                "INSERT INTO admins (id, username, password) VALUES (?, ?, ?)",
                (1, "admin", generate_password_hash("admin123")),
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


@app.before_request
def ensure_database() -> None:
    init_db()


@app.after_request
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
    return text


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
        row = db.execute("SELECT id, username FROM admins WHERE id = ?", (admin_id,)).fetchone()
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
        return jsonify({"error": "invalid category data"}), 400

    with get_db() as db:
        try:
            cursor = db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            db.commit()
            row = db.execute("SELECT name FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone()
        except sqlite3.IntegrityError:
            return jsonify({"error": "category already exists"}), 409

    return jsonify({"name": row["name"]}), 201


@app.route("/api/categories/<path:category_name>", methods=["DELETE"])
@login_required
def api_delete_category(category_name: str):
    require_csrf()
    with get_db() as db:
        if db.execute("SELECT id FROM products WHERE category = ?", (category_name,)).fetchone() is not None:
            return jsonify({"error": "category is in use"}), 409
        db.execute("DELETE FROM categories WHERE name = ?", (category_name,))
        db.commit()
    return jsonify({"message": "deleted"})


@app.route("/api/products", methods=["GET"])
def api_get_products():
    with get_db() as db:
        rows = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return jsonify([row_to_product(row) for row in rows])


@app.route("/api/products/<int:product_id>", methods=["GET"])
def api_get_product(product_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(row_to_product(row))


@app.route("/api/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or request.form
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    with get_db() as db:
        row = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()

    if row is None or not check_password_hash(row["password"], password):
        return jsonify({"error": "invalid credentials"}), 401

    session.clear()
    session[SESSION_ADMIN_KEY] = row["id"]
    session[SESSION_CSRF_KEY] = secrets.token_urlsafe(32)
    return jsonify({"message": "logged in", "admin": {"id": row["id"], "username": row["username"]}, "csrfToken": session[SESSION_CSRF_KEY]})


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    require_csrf()
    session.clear()
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
        return jsonify({"error": "image file required"}), 400
    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "image file required"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "unsupported file type"}), 400

    filename = secure_filename(file.filename)
    unique_prefix = secrets.token_hex(8)
    final_name = f"{unique_prefix}_{filename}"
    save_path = UPLOAD_FOLDER / final_name
    file.save(save_path)
    return jsonify({"message": "uploaded", "filename": final_name, "url": url_for("uploaded_product_image", filename=final_name)})


@app.route("/api/products", methods=["POST"])
@login_required
def api_create_product():
    require_csrf()
    payload = request.get_json(silent=True) or request.form
    try:
        name = normalize_text(payload.get("name"), 120)
        description = normalize_text(payload.get("description"), 1000)
        category = normalize_text(payload.get("category"), 80)
        price = sanitize_float(payload.get("price"), 0)
        stock = sanitize_int(payload.get("stock"), 0)
        image = str(payload.get("image", "")).strip()
    except (TypeError, ValueError):
        return jsonify({"error": "invalid product data"}), 400

    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO products (name, description, price, category, stock, image) VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, price, category, stock, image),
        )
        db.commit()
        row = db.execute("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(row_to_product(row)), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@login_required
def api_update_product(product_id: int):
    require_csrf()
    payload = request.get_json(silent=True) or request.form
    with get_db() as db:
        existing = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "not found"}), 404

        try:
            name = normalize_text(payload.get("name", existing["name"]), 120)
            description = normalize_text(payload.get("description", existing["description"]), 1000)
            category = normalize_text(payload.get("category", existing["category"]), 80)
            price = sanitize_float(payload.get("price", existing["price"]), 0)
            stock = sanitize_int(payload.get("stock", existing["stock"]), 0)
            image = str(payload.get("image", existing["image"]) or "").strip()
        except (TypeError, ValueError):
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
        row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(row_to_product(row))


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@login_required
def api_delete_product(product_id: int):
    require_csrf()
    with get_db() as db:
        existing = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "not found"}), 404
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
    return jsonify({"message": "deleted"})


@app.errorhandler(404)
def handle_404(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found"}), 404
    return redirect(url_for("index"))


@app.errorhandler(413)
def handle_413(_error):
    return jsonify({"error": "file too large"}), 413


@app.context_processor
def inject_globals():
    with get_db() as db:
        categories = [row["name"] for row in db.execute("SELECT name FROM categories ORDER BY name ASC").fetchall()]
    return {"logged_in_admin": current_admin(), "product_categories": categories}


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
