"""
Test suite for the cosmetics store Flask application.
"""

import importlib
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("INITIAL_ADMIN_USERNAME", "admin")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("DISABLE_RATE_LIMITING", "true")

import app as app_module

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("INITIAL_ADMIN_USERNAME", "admin")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "admin123")


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()
    temp_db_path = Path(temp_db.name)
    
    # Override database path
    original_db_path = app_module.DATABASE_PATH
    app_module.DATABASE_PATH = temp_db_path
    
    # Create upload folder
    upload_folder = temp_db_path.parent / "uploads" / "products"
    upload_folder.mkdir(parents=True, exist_ok=True)
    app_module.UPLOAD_FOLDER = upload_folder
    app_module.app.config["UPLOAD_FOLDER"] = str(upload_folder)
    
    # Initialize database
    app_module.init_db()
    
    # Create test client
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    
    yield client
    
    # Cleanup
    app_module.DATABASE_PATH = original_db_path
    # Close all database connections
    import gc
    gc.collect()
    import time
    time.sleep(0.1)  # Give SQLite time to release locks
    if temp_db_path.exists():
        try:
            temp_db_path.unlink()
        except (PermissionError, OSError):
            pass  # Ignore cleanup errors on Windows


def test_app_uses_fallback_secret_key_when_env_missing(monkeypatch):
    """App should still start even if SECRET_KEY is not set in deployment env."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import app as app_module
    reloaded_module = importlib.reload(app_module)
    assert reloaded_module.app.config["SECRET_KEY"]


def test_database_adapter_wraps_psycopg_style_connections():
    """The DB adapter should expose execute/executemany for psycopg-style connections."""

    class FakeCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((query, params))
            return None

        def executemany(self, query, params_seq):
            self.calls.append((query, params_seq))
            return None

        def fetchone(self):
            return None

        def fetchall(self):
            return []

    class FakeConnection:
        def __init__(self):
            self.commit_calls = 0
            self.rollback_calls = 0

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.commit_calls += 1

        def rollback(self):
            self.rollback_calls += 1

    adapter = app_module.DatabaseAdapter(FakeConnection())
    cursor = adapter.execute("SELECT 1")
    assert cursor is not None
    cursor = adapter.executemany("INSERT INTO test VALUES (?)", [(1,)])
    assert cursor is not None


class TestPublicPages:
    """Test public-facing pages."""
    
    def test_index_page(self, client):
        """Test index page loads."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.data
    
    def test_product_page(self, client):
        """Test product page loads."""
        response = client.get("/product/1")
        assert response.status_code == 200
        assert b"html" in response.data
    
    def test_cart_page(self, client):
        """Test cart page loads."""
        response = client.get("/cart")
        assert response.status_code == 200
        assert b"html" in response.data
    
    def test_checkout_page(self, client):
        """Test checkout page loads."""
        response = client.get("/checkout")
        assert response.status_code == 200
        assert b"html" in response.data
    
    def test_404_redirect_to_index(self, client):
        """Test non-API 404s redirect to index."""
        response = client.get("/nonexistent", follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/")


class TestProductsAPI:
    """Test products API endpoints."""
    
    def test_get_all_products(self, client):
        """Test retrieving all products."""
        response = client.get("/api/products")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 4  # 4 seeded products
        assert all("id" in p and "name" in p and "price" in p for p in data)
    
    def test_get_product_by_id(self, client):
        """Test retrieving a specific product."""
        response = client.get("/api/products/1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["id"] == 1
        assert "name" in data
        assert "price" in data
        assert "stock" in data
    
    def test_get_nonexistent_product(self, client):
        """Test getting non-existent product returns 404."""
        response = client.get("/api/products/999")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error"] == "not found"
    
    def test_products_are_ordered_by_id_desc(self, client):
        """Test products are returned in descending order by ID."""
        response = client.get("/api/products")
        data = json.loads(response.data)
        ids = [p["id"] for p in data]
        assert ids == sorted(ids, reverse=True)


class TestAdminLogin:
    """Test admin authentication."""
    
    def test_login_page_loads(self, client):
        """Test admin login page loads."""
        response = client.get("/admin-login")
        assert response.status_code == 200
        assert b"html" in response.data
    
    def test_login_with_correct_credentials(self, client):
        """Test login with correct credentials."""
        response = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["message"] == "logged in"
        assert data["admin"]["username"] == "admin"
        assert "csrfToken" in data
    
    def test_login_with_wrong_password(self, client):
        """Test login with wrong password."""
        response = client.post(
            "/api/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error"] == "invalid credentials"
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/login",
            json={"username": "nonexistent", "password": "password"}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error"] == "invalid credentials"
    
    def test_login_without_credentials(self, client):
        """Test login without credentials."""
        response = client.post(
            "/api/login",
            json={"username": "", "password": ""}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "username and password are required"
    
    def test_login_redirects_already_logged_in(self, client):
        """Test login page redirects if already logged in."""
        # Login first
        client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        # Try to access login page
        response = client.get("/admin-login", follow_redirects=False)
        assert response.status_code == 302
        assert "admin-dashboard" in response.location


class TestAdminDashboard:
    """Test admin dashboard and protected routes."""
    
    def test_dashboard_requires_login(self, client):
        """Test admin dashboard requires authentication."""
        response = client.get("/admin-dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "login" in response.location
    
    def test_dashboard_loads_when_logged_in(self, client):
        """Test admin dashboard loads when logged in."""
        # Login
        client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        response = client.get("/admin-dashboard")
        assert response.status_code == 200
        assert b"html" in response.data
    
    def test_logout(self, client):
        """Test logout functionality."""
        # Login first
        login_response = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        csrf_token = json.loads(login_response.data)["csrfToken"]
        
        # Logout
        response = client.post(
            "/api/logout",
            headers={"X-CSRF-Token": csrf_token},
            json={}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["message"] == "logged out"
    
    def test_session_endpoint(self, client):
        """Test session endpoint returns correct info."""
        # Login first
        client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        response = client.get("/api/session")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["authenticated"] is True
        assert data["admin"]["username"] == "admin"
        assert "csrfToken" in data


class TestProductCRUD:
    """Test product CRUD operations."""
    
    def _login_and_get_csrf(self, client):
        """Helper to login and get CSRF token."""
        response = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        data = json.loads(response.data)
        return data["csrfToken"]
    
    def test_create_product_without_login(self, client):
        """Test creating product requires login."""
        response = client.post(
            "/api/products",
            json={
                "name": "Test Product",
                "description": "Test",
                "price": 10.0,
                "category": "Face",
                "stock": 5,
                "image": ""
            }
        )
        assert response.status_code == 401
    
    def test_create_product_without_csrf(self, client):
        """Test creating product without CSRF token fails."""
        self._login_and_get_csrf(client)
        response = client.post(
            "/api/products",
            json={
                "name": "Test Product",
                "description": "Test",
                "price": 10.0,
                "category": "Face",
                "stock": 5,
                "image": ""
            }
        )
        assert response.status_code == 403
    
    def test_create_product_successfully(self, client):
        """Test creating a product successfully."""
        csrf_token = self._login_and_get_csrf(client)
        
        response = client.post(
            "/api/products",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "name": "New Product",
                "description": "A new cosmetic product",
                "price": 29.99,
                "category": "Lips",
                "stock": 15,
                "image": "/static/images/placeholder.svg"
            }
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["name"] == "New Product"
        assert data["price"] == 29.99
        assert data["category"] == "Lips"
        assert data["stock"] == 15
    
    def test_create_product_invalid_data(self, client):
        """Test creating product with invalid data."""
        csrf_token = self._login_and_get_csrf(client)
        
        response = client.post(
            "/api/products",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "name": "",  # Invalid: empty name
                "description": "Test",
                "price": 10.0,
                "category": "Face",
                "stock": 5,
                "image": ""
            }
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_update_product(self, client):
        """Test updating a product."""
        csrf_token = self._login_and_get_csrf(client)
        
        response = client.put(
            "/api/products/1",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "name": "Updated Name",
                "price": 99.99
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == "Updated Name"
        assert data["price"] == 99.99
    
    def test_update_nonexistent_product(self, client):
        """Test updating non-existent product."""
        csrf_token = self._login_and_get_csrf(client)
        
        response = client.put(
            "/api/products/999",
            headers={"X-CSRF-Token": csrf_token},
            json={"name": "Updated"}
        )
        assert response.status_code == 404
    
    def test_delete_product(self, client):
        """Test deleting a product."""
        csrf_token = self._login_and_get_csrf(client)
        
        # First verify product exists
        response = client.get("/api/products/1")
        assert response.status_code == 200
        
        # Delete it
        response = client.delete(
            "/api/products/1",
            headers={"X-CSRF-Token": csrf_token}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["message"] == "deleted"
        
        # Verify it's gone
        response = client.get("/api/products/1")
        assert response.status_code == 404
    
    def test_delete_nonexistent_product(self, client):
        """Test deleting non-existent product."""
        csrf_token = self._login_and_get_csrf(client)
        
        response = client.delete(
            "/api/products/999",
            headers={"X-CSRF-Token": csrf_token}
        )
        assert response.status_code == 404


class TestCategoriesManagement:
    """Test category management endpoints."""

    def _login_and_get_csrf(self, client):
        response = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"},
        )
        return json.loads(response.data)["csrfToken"]

    def test_get_categories(self, client):
        response = client.get("/api/categories")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert "Lips" in data

    def test_create_category(self, client):
        csrf_token = self._login_and_get_csrf(client)
        response = client.post(
            "/api/categories",
            headers={"X-CSRF-Token": csrf_token},
            json={"name": "Glow"},
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["name"] == "Glow"

    def test_delete_category(self, client):
        csrf_token = self._login_and_get_csrf(client)
        client.post(
            "/api/categories",
            headers={"X-CSRF-Token": csrf_token},
            json={"name": "Fresh"},
        )
        response = client.delete(
            "/api/categories/Fresh",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["message"] == "deleted"


class TestCSRFProtection:
    """Test CSRF protection."""
    
    def test_logout_csrf_protection(self, client):
        """Test logout requires valid CSRF token."""
        # Login
        client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        # Try logout without CSRF token
        response = client.post("/api/logout", json={})
        assert response.status_code == 403
        
        # Try logout with wrong CSRF token
        response = client.post(
            "/api/logout",
            headers={"X-CSRF-Token": "wrong-token"},
            json={}
        )
        assert response.status_code == 403


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_allowed_file(self):
        """Test file validation."""
        assert app_module.allowed_file("image.png") is True
        assert app_module.allowed_file("photo.jpg") is True
        assert app_module.allowed_file("picture.gif") is True
        assert app_module.allowed_file("document.pdf") is False
        assert app_module.allowed_file("script.exe") is False
        assert app_module.allowed_file("noextension") is False
    
    def test_sanitize_int(self):
        """Test integer sanitization."""
        assert app_module.sanitize_int(5) == 5
        assert app_module.sanitize_int("10") == 10
        
        with pytest.raises(ValueError):
            app_module.sanitize_int(-5, minimum=0)
        
        with pytest.raises(ValueError):
            app_module.sanitize_int("not-a-number")
    
    def test_sanitize_float(self):
        """Test float sanitization."""
        assert app_module.sanitize_float(5.5) == 5.5
        assert app_module.sanitize_float("10.99") == 10.99
        
        with pytest.raises(ValueError):
            app_module.sanitize_float(-5.0, minimum=0)
        
        with pytest.raises(ValueError):
            app_module.sanitize_float("not-a-number")
    
    def test_normalize_text(self):
        """Test text normalization."""
        assert app_module.normalize_text("  hello  ") == "hello"
        assert app_module.normalize_text("test") == "test"
        
        with pytest.raises(ValueError):
            app_module.normalize_text("")
        
        with pytest.raises(ValueError):
            app_module.normalize_text("x" * 501, max_length=500)
