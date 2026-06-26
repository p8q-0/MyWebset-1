(function () {
  let csrfToken = localStorage.getItem("cosmetics_store_csrf") || "";

  function formatMoney(value) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(value || 0));
  }

  function showToast(message, type = "info") {
    const stack = document.querySelector("[data-toast-stack]");
    if (!stack) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    stack.appendChild(toast);
    window.setTimeout(() => toast.remove(), 3200);
  }

  async function fetchJSON(url) {
    const response = await fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache",
        Pragma: "no-cache",
      },
    });
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    return response.json();
  }

  async function adminFetch(url, options = {}) {
    const method = String(options.method || "GET").toUpperCase();
    const headers = { ...(options.headers || {}) };
    if (method !== "GET") {
      headers["X-CSRF-Token"] = csrfToken;
    }
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = headers["Content-Type"] || "application/json";
    }

    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
      headers,
    });

    if (!response.ok) {
      let message = "Request failed";
      try {
        const errorBody = await response.json();
        message = errorBody.error || message;
      } catch (error) {
        message = `Request failed with ${response.status}`;
      }
      throw new Error(message);
    }

    return response.json();
  }

  function setPreview(imagePath, name) {
    const preview = document.querySelector("[data-image-preview]");
    if (!preview) return;
    preview.innerHTML = imagePath
      ? `<img src="${imagePath}" alt="${name || 'Product preview'}">`
      : '<div class="empty-state" style="display:grid; place-items:center; height:100%;">Image preview will appear here</div>';
  }

  function resetForm() {
    const form = document.querySelector("[data-product-form]");
    if (!form) return;
    form.reset();
    form.querySelector('[name="id"]').value = "";
    form.querySelector('[name="image"]').value = "";
    form.querySelector('[data-submit-label]').textContent = "Add product";
    setPreview("", "");
  }

  function renderCategoryOptions(categories) {
    const select = document.querySelector("[data-product-form] select[name='category']");
    if (!select) return;
    const currentValue = select.value;
    select.innerHTML = `<option value="">Select a category</option>${categories
      .map((category) => `<option value="${category}">${category}</option>`)
      .join("")}`;
    if (currentValue) {
      select.value = currentValue;
    }
  }

  function renderCategoryList(categories) {
    const list = document.querySelector("[data-category-list]");
    if (!list) return;
    list.innerHTML = categories.length
      ? `<ul class="category-chip-list">${categories
          .map(
            (category) => `
              <li class="category-chip">
                <span>${category}</span>
                <button type="button" data-delete-category="${category}">Delete</button>
              </li>
            `
          )
          .join("")}</ul>`
      : '<div class="empty-state">No categories yet.</div>';

    list.querySelectorAll("[data-delete-category]").forEach((button) => {
      button.addEventListener("click", () => deleteCategory(button.getAttribute("data-delete-category")));
    });
  }

  function fillForm(product) {
    const form = document.querySelector("[data-product-form]");
    if (!form) return;
    form.querySelector('[name="id"]').value = product.id;
    form.querySelector('[name="name"]').value = product.name;
    form.querySelector('[name="category"]').value = product.category;
    form.querySelector('[name="description"]').value = product.description;
    form.querySelector('[name="price"]').value = product.price;
    form.querySelector('[name="stock"]').value = product.stock;
    form.querySelector('[name="image"]').value = product.image;
    form.querySelector('[data-submit-label]').textContent = "Update product";
    setPreview(product.image, product.name);
  }

  function renderTable(products) {
    const tbody = document.querySelector("[data-admin-product-table]");
    if (!tbody) return;
    tbody.innerHTML = products.length
      ? products.map((product) => `
          <tr>
            <td>
              <strong>${product.name}</strong>
              <div class="muted">#${product.id}</div>
            </td>
            <td>${product.category}</td>
            <td>${formatMoney(product.price)}</td>
            <td>${product.stock}</td>
            <td>
              <div class="row-actions">
                <button class="secondary-button" type="button" data-edit-product="${product.id}">Edit</button>
                <button class="ghost-button" type="button" data-delete-product="${product.id}">Delete</button>
              </div>
            </td>
          </tr>
        `).join("")
      : '<tr><td colspan="5" class="empty-state" style="text-align:center; padding: 24px;">No products found.</td></tr>';

    products.forEach((product) => {
      tbody.querySelector(`[data-edit-product="${product.id}"]`).addEventListener("click", () => fillForm(product));
      tbody.querySelector(`[data-delete-product="${product.id}"]`).addEventListener("click", () => deleteProduct(product.id, product.name));
    });
  }

  async function loadSession() {
    const userChip = document.querySelector("[data-admin-user]");
    try {
      const response = await adminFetch("/api/session", { method: "GET" });
      csrfToken = response.csrfToken || csrfToken;
      localStorage.setItem("cosmetics_store_csrf", csrfToken);
      if (userChip) {
        userChip.textContent = `Signed in as ${response.admin.username}`;
      }
      localStorage.setItem("adminAuthenticated", "true");
    } catch (error) {
      localStorage.removeItem("adminAuthenticated");
      localStorage.removeItem("cosmetics_store_csrf");
      window.location.href = "/admin-login";
    }
  }

  async function loadProducts() {
    try {
      const products = await fetchJSON("/api/products");
      renderTable(products);
    } catch (error) {
      showToast(error.message || "Unable to load products", "error");
    }
  }

  async function loadCategories() {
    try {
      const categories = await fetchJSON("/api/categories");
      renderCategoryOptions(categories);
      renderCategoryList(categories);
    } catch (error) {
      showToast(error.message || "Unable to load categories", "error");
    }
  }

  async function uploadImageIfNeeded(fileInput, fallbackName) {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return null;
    const formData = new FormData();
    formData.append("image", file);
    const data = await adminFetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    setPreview(data.url, fallbackName);
    return data.url;
  }

  async function submitProductForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const productId = String(formData.get("id") || "").trim();

    try {
      const uploadedImagePath = await uploadImageIfNeeded(form.querySelector('[name="image_file"]'), String(formData.get("name") || ""));
      const payload = {
        name: String(formData.get("name") || "").trim(),
        category: String(formData.get("category") || "").trim(),
        description: String(formData.get("description") || "").trim(),
        price: Number(formData.get("price") || 0),
        stock: Number(formData.get("stock") || 0),
        image: uploadedImagePath || String(formData.get("image") || "").trim(),
      };

      const isEditing = Boolean(productId);
      const savedProduct = await adminFetch(isEditing ? `/api/products/${productId}` : "/api/products", {
        method: isEditing ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });

      showToast(`${savedProduct.name} saved successfully`, "success");
      localStorage.setItem("catalog_updated_at", String(Date.now()));
      if (typeof BroadcastChannel !== "undefined") {
        new BroadcastChannel("catalog-updates").postMessage({ type: "catalog-updated" });
      }
      resetForm();
      await loadProducts();
    } catch (error) {
      showToast(error.message || "Unable to save product", "error");
    }
  }

  async function deleteProduct(productId, productName) {
    const confirmed = window.confirm(`Delete ${productName}? This cannot be undone.`);
    if (!confirmed) return;
    try {
      await adminFetch(`/api/products/${productId}`, { method: "DELETE" });
      showToast(`${productName} deleted`, "success");
      localStorage.setItem("catalog_updated_at", String(Date.now()));
      if (typeof BroadcastChannel !== "undefined") {
        new BroadcastChannel("catalog-updates").postMessage({ type: "catalog-updated" });
      }
      await loadProducts();
      resetForm();
    } catch (error) {
      showToast(error.message || "Unable to delete product", "error");
    }
  }

  async function submitLogin(event) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    try {
      const response = await adminFetch("/api/login", {
        method: "POST",
        body: JSON.stringify({
          username: String(formData.get("username") || "").trim(),
          password: String(formData.get("password") || "").trim(),
        }),
      });
      csrfToken = response.csrfToken || csrfToken;
      localStorage.setItem("cosmetics_store_csrf", csrfToken);
      localStorage.setItem("adminAuthenticated", "true");
      showToast("Login successful", "success");
      window.location.href = "/admin-dashboard";
    } catch (error) {
      showToast(error.message || "Login failed", "error");
    }
  }

  async function submitCategoryForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const categoryName = String(formData.get("category_name") || "").trim();
    if (!categoryName) return;

    try {
      await adminFetch("/api/categories", {
        method: "POST",
        body: JSON.stringify({ name: categoryName }),
      });
      form.reset();
      showToast(`Category ${categoryName} added`, "success");
      await loadCategories();
    } catch (error) {
      showToast(error.message || "Unable to add category", "error");
    }
  }

  async function deleteCategory(categoryName) {
    const confirmed = window.confirm(`Delete category ${categoryName}? It can only be removed if no products use it.`);
    if (!confirmed) return;

    try {
      await adminFetch(`/api/categories/${encodeURIComponent(categoryName)}`, { method: "DELETE" });
      showToast(`${categoryName} deleted`, "success");
      await loadCategories();
      await loadProducts();
    } catch (error) {
      showToast(error.message || "Unable to delete category", "error");
    }
  }

  const loginForm = document.querySelector("[data-admin-login-form]");
  if (loginForm) {
    loginForm.addEventListener("submit", submitLogin);
    return;
  }

  const dashboard = document.querySelector("[data-admin-dashboard]");
  if (!dashboard) return;

  loadSession();
  loadCategories();
  loadProducts();

  const form = document.querySelector("[data-product-form]");
  if (form) {
    form.addEventListener("submit", submitProductForm);
    form.querySelector('[name="image_file"]').addEventListener("change", (event) => {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      setPreview(URL.createObjectURL(file), file.name);
    });
  }

  const categoryForm = document.querySelector("[data-category-form]");
  if (categoryForm) {
    categoryForm.addEventListener("submit", submitCategoryForm);
  }

  const resetButton = document.querySelector("[data-reset-form]");
  if (resetButton) resetButton.addEventListener("click", resetForm);
  const refreshButton = document.querySelector("[data-refresh-products]");
  if (refreshButton) refreshButton.addEventListener("click", loadProducts);
  setPreview("", "");
})();
