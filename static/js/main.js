(function () {
  const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
  const cartKey = "cosmetics_store_cart";
  const orderKey = "cosmetics_store_order_counter";

  function formatMoney(value) {
    return currency.format(Number(value || 0));
  }

  function getCart() {
    try {
      return JSON.parse(localStorage.getItem(cartKey) || "[]");
    } catch (error) {
      return [];
    }
  }

  function saveCart(cart) {
    localStorage.setItem(cartKey, JSON.stringify(cart));
    updateCartBadge();
  }

  function updateCartBadge() {
    const count = getCart().reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    document.querySelectorAll("[data-cart-count]").forEach((element) => {
      element.textContent = String(count);
    });
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

  function getOrderSequence() {
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    const storageKey = `${orderKey}_${today}`;
    const currentValue = Number(localStorage.getItem(storageKey) || "0") + 1;
    localStorage.setItem(storageKey, String(currentValue));
    return String(currentValue).padStart(3, "0");
  }

  function createOrderId() {
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    return `ORD-${today}-${getOrderSequence()}`;
  }

  function addToCart(product) {
    const cart = getCart();
    const index = cart.findIndex((item) => Number(item.id) === Number(product.id));
    if (index >= 0) {
      cart[index].quantity += 1;
    } else {
      cart.push({
        id: product.id,
        name: product.name,
        price: Number(product.price),
        image: product.image,
        category: product.category,
        stock: Number(product.stock),
        quantity: 1,
      });
    }
    saveCart(cart);
    showToast(`${product.name} added to cart`, "success");
  }

  function removeFromCart(productId) {
    const cart = getCart().filter((item) => Number(item.id) !== Number(productId));
    saveCart(cart);
    showToast("Item removed from cart", "info");
  }

  function updateItemQuantity(productId, delta) {
    const cart = getCart();
    const item = cart.find((entry) => Number(entry.id) === Number(productId));
    if (!item) return;
    item.quantity += delta;
    if (item.quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    saveCart(cart);
    renderCart();
    renderCheckoutSummary();
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

  async function fetchProducts() {
    return fetchJSON("/api/products");
  }

  async function fetchCategories() {
    return fetchJSON("/api/categories");
  }

  async function loadCategories() {
    const categoryFilter = document.querySelector("#category-filter");
    if (!categoryFilter) return;

    try {
      const categories = await fetchCategories();
      categoryFilter.innerHTML = `
        <option value="">All products</option>
        ${categories.map((category) => `<option value="${category}">${category}</option>`).join("")}
      `;
    } catch (error) {
      categoryFilter.innerHTML = `<option value="">All products</option>`;
      showToast("Unable to load categories", "error");
    }
  }

  async function renderProducts() {
    const grid = document.querySelector("[data-product-grid]");
    if (!grid) return;

    try {
      const allProducts = await fetchProducts();
      const categoryFilter = document.querySelector("#category-filter");
      const selectedCategory = categoryFilter ? categoryFilter.value : "";

      const filteredProducts = selectedCategory
        ? allProducts.filter((p) => p.category === selectedCategory)
        : allProducts;

      grid.innerHTML = "";
      if (filteredProducts.length === 0) {
        grid.innerHTML = `
          <div class="panel-card empty-state" style="grid-column: 1 / -1; text-align: center;">
            <h2>No products found</h2>
            <p>${selectedCategory ? `No products in the ${selectedCategory} category.` : "Add products to populate the storefront."}</p>
          </div>
        `;
        return;
      }
      filteredProducts.forEach((product) => grid.appendChild(renderProductCard(product)));
    } catch (error) {
      grid.innerHTML = `
        <div class="panel-card empty-state" style="grid-column: 1 / -1; text-align: center;">
          <h2>Unable to load products</h2>
          <p>Please refresh the page or check the backend server.</p>
        </div>
      `;
      showToast("Product catalogue could not be loaded", "error");
    }
  }

  function renderProductCard(product) {
    const card = document.createElement("article");
    card.className = "product-card";
    card.innerHTML = `
      <a class="product-media" href="/product/${product.id}">
        <img src="${product.image}" alt="${product.name}" loading="lazy" decoding="async" width="400" height="400">
      </a>
      <div class="product-body">
        <div class="product-meta">
          <span>${product.category}</span>
          <strong>${formatMoney(product.price)}</strong>
        </div>
        <h3><a href="/product/${product.id}">${product.name}</a></h3>
        <p>${product.description}</p>
        <div class="product-actions">
          <button class="primary-button" type="button" data-add-product="${product.id}">Add to cart</button>
          <a class="secondary-button" href="/product/${product.id}">View details</a>
        </div>
      </div>
    `;
    card.querySelector("[data-add-product]").addEventListener("click", () => addToCart(product));
    return card;
  }

  async function renderHomeProducts() {
    return renderProducts();
  }

  async function renderProductDetails() {
    const shell = document.querySelector("[data-product-page]");
    if (!shell) return;
    const productId = shell.getAttribute("data-product-id");
    try {
      const product = await fetchJSON(`/api/products/${productId}`);
      shell.querySelector("[data-product-category]").textContent = product.category;
      shell.querySelector("[data-product-name]").textContent = product.name;
      shell.querySelector("[data-product-description]").textContent = product.description;
      shell.querySelector("[data-product-price]").textContent = formatMoney(product.price);
      shell.querySelector("[data-product-stock]").textContent = `${product.stock} in stock`;
      const imageContainer = shell.querySelector("[data-product-image]");
      imageContainer.innerHTML = `<img src="${product.image}" alt="${product.name}">`;
      imageContainer.classList.remove("placeholder-surface");
      shell.querySelector("[data-add-to-cart]").addEventListener("click", () => addToCart(product));
    } catch (error) {
      showToast("Product details could not be loaded", "error");
    }
  }

  function renderCart() {
    const panel = document.querySelector("[data-cart-items]");
    const emptyState = document.querySelector("[data-cart-empty]");
    const summaryCount = document.querySelector("[data-summary-count]");
    const summaryTotal = document.querySelector("[data-summary-total]");
    if (!panel) return;

    const cart = getCart();
    const totalItems = cart.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const totalPrice = cart.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.price || 0), 0);
    if (summaryCount) summaryCount.textContent = String(totalItems);
    if (summaryTotal) summaryTotal.textContent = formatMoney(totalPrice);
    panel.innerHTML = "";

    if (cart.length === 0) {
      if (emptyState) emptyState.style.display = "grid";
      return;
    }

    if (emptyState) emptyState.style.display = "none";

    cart.forEach((item) => {
      const cartItem = document.createElement("article");
      cartItem.className = "cart-item";
      cartItem.innerHTML = `
        <img src="${item.image}" alt="${item.name}" loading="lazy" decoding="async" width="96" height="96">
        <div>
          <strong>${item.name}</strong>
          <div class="muted">${item.category} · ${formatMoney(item.price)} each</div>
          <div class="qty-control" aria-label="Quantity controls">
            <button type="button" data-dec>-</button>
            <strong>${item.quantity}</strong>
            <button type="button" data-inc>+</button>
          </div>
        </div>
        <div>
          <strong>${formatMoney(item.quantity * item.price)}</strong>
          <div class="row-actions" style="margin-top: 10px;">
            <button class="ghost-button" type="button" data-remove>Remove</button>
          </div>
        </div>
      `;
      cartItem.querySelector("[data-dec]").addEventListener("click", () => updateItemQuantity(item.id, -1));
      cartItem.querySelector("[data-inc]").addEventListener("click", () => updateItemQuantity(item.id, 1));
      cartItem.querySelector("[data-remove]").addEventListener("click", () => removeFromCart(item.id));
      panel.appendChild(cartItem);
    });
  }

  function renderCheckoutSummary() {
    const list = document.querySelector("[data-checkout-items]");
    const total = document.querySelector("[data-checkout-total]");
    if (!list || !total) return;
    const cart = getCart();
    const totalPrice = cart.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.price || 0), 0);
    list.innerHTML = cart.length
      ? cart.map((item) => `
          <div class="summary-row">
            <span>${item.quantity} x ${item.name}</span>
            <strong>${formatMoney(item.quantity * item.price)}</strong>
          </div>
        `).join("")
      : '<p class="muted">Your cart is empty. Add products before checkout.</p>';
    total.textContent = formatMoney(totalPrice);
  }

  function handleCheckoutSubmit() {
    const form = document.querySelector("[data-checkout-form]");
    if (!form) return;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const cart = getCart();
      if (cart.length === 0) {
        showToast("Add products to the cart before checkout", "error");
        return;
      }

      const formData = new FormData(form);
      const customerName = String(formData.get("name") || "").trim();
      const customerPhone = String(formData.get("phone") || "").trim();
      const customerAddress = String(formData.get("address") || "").trim();
      const customerNotes = String(formData.get("notes") || "").trim();
      if (!customerName || !customerPhone || !customerAddress) {
        showToast("Please complete the checkout form", "error");
        return;
      }

      const orderId = createOrderId();
      const totalPrice = cart.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.price || 0), 0);
      const productLines = cart.map((item) => `- ${item.quantity} x ${item.name} (${formatMoney(item.price)} each) = ${formatMoney(item.quantity * item.price)}`).join("\n");
      const message = [
        `Order ID: ${orderId}`,
        "",
        "Customer Information:",
        `Name: ${customerName}`,
        `Phone: ${customerPhone}`,
        `Address: ${customerAddress}`,
        `Notes: ${customerNotes || "None"}`,
        "",
        "Products:",
        productLines,
        "",
        `Total: ${formatMoney(totalPrice)}`,
      ].join("\n");

      window.open(`https://wa.me/201022170260?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
      localStorage.removeItem(cartKey);
      updateCartBadge();
      renderCart();
      renderCheckoutSummary();
      form.reset();
      showToast(`Order ${orderId} prepared for WhatsApp`, "success");
    });
  }

  const navToggle = document.querySelector("[data-nav-toggle]");
  const siteNav = document.querySelector(".site-nav");
  if (navToggle && siteNav) {
    navToggle.addEventListener("click", () => {
      const isOpen = siteNav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      document.body.classList.toggle("nav-open", isOpen);
    });
    siteNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        siteNav.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
        document.body.classList.remove("nav-open");
      });
    });
  }

  updateCartBadge();
  renderHomeProducts();
  renderProductDetails();
  renderCart();
  renderCheckoutSummary();
  handleCheckoutSubmit();

  const categoryFilter = document.querySelector("#category-filter");
  if (categoryFilter) {
    categoryFilter.addEventListener("change", renderProducts);
    loadCategories();
  }

  const catalogChannel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("catalog-updates") : null;
  if (catalogChannel) {
    catalogChannel.onmessage = (event) => {
      if (event.data && event.data.type === "catalog-updated") {
        loadCategories();
        renderHomeProducts();
        renderProductDetails();
      }
    };
  }

  window.addEventListener("storage", (event) => {
    if (event.key === "catalog_updated_at") {
      renderHomeProducts();
      renderProductDetails();
    }
  });

  window.addEventListener("focus", () => {
    renderHomeProducts();
    renderProductDetails();
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      loadCategories();
      renderHomeProducts();
      renderProductDetails();
    }
  });

  window.CosmeticsStore = {
    addToCart,
    getCart,
    saveCart,
    showToast,
    formatMoney,
    fetchJSON,
    fetchProducts,
    fetchCategories,
    loadCategories,
    renderProducts,
    renderCart,
    renderCheckoutSummary,
  };
})();
