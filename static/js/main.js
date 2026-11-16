(function () {
  const currencyLocale = (document.documentElement.lang || "en").toLowerCase().startsWith("ar") ? "ar-EG" : "en-EG";
  const currency = new Intl.NumberFormat(currencyLocale, { style: "currency", currency: "EGP" });
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

  let productSearchIndex = [];

  function normalizeProductSearchText(value) {
    return String(value || "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/[\u0640]/g, "")
      .replace(/[^\p{L}\p{N}\s]/gu, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function levenshteinDistance(left, right) {
    if (left === right) return 0;
    if (left.length === 0) return right.length;
    if (right.length === 0) return left.length;

    const dp = Array.from({ length: left.length + 1 }, () => new Array(right.length + 1).fill(0));
    for (let i = 0; i <= left.length; i += 1) dp[i][0] = i;
    for (let j = 0; j <= right.length; j += 1) dp[0][j] = j;

    for (let i = 1; i <= left.length; i += 1) {
      for (let j = 1; j <= right.length; j += 1) {
        const substitutionCost = left[i - 1] === right[j - 1] ? 0 : 1;
        dp[i][j] = Math.min(
          dp[i - 1][j] + 1,
          dp[i][j - 1] + 1,
          dp[i - 1][j - 1] + substitutionCost,
        );
      }
    }

    return dp[left.length][right.length];
  }

  function buildProductSearchIndex(products) {
    return products.map((product) => {
      const normalizedName = normalizeProductSearchText(product.name);
      return {
        id: product.id,
        product,
        normalizedName,
        words: normalizedName ? normalizedName.split(/\s+/).filter(Boolean) : [],
      };
    });
  }

  function getProductSearchIndex(products) {
    if (
      !productSearchIndex.length ||
      productSearchIndex.length !== products.length ||
      productSearchIndex.some((entry, index) => Number(entry.id) !== Number(products[index]?.id))
    ) {
      productSearchIndex = buildProductSearchIndex(products);
    }
    return productSearchIndex;
  }

  function scoreProductNameMatch(entry, query) {
    if (!query) return 0;
    if (!entry || !entry.normalizedName) return 0;

    const target = entry.normalizedName;
    const queryWords = query.split(/\s+/).filter(Boolean);
    if (!queryWords.length) return 0;

    if (target === query) return 100000;
    if (target.startsWith(query)) return 90000;
    if (target.includes(query)) return 70000;

    let score = 0;
    const allWordsMatched = queryWords.every((queryWord) => {
      if (entry.words.includes(queryWord)) return true;
      return entry.words.some((word) => word.startsWith(queryWord) || queryWord.startsWith(word));
    });

    if (allWordsMatched) {
      score += 5000;
    }

    for (const queryWord of queryWords) {
      if (entry.words.includes(queryWord)) {
        score += 2500;
        continue;
      }

      const fuzzyCandidate = entry.words.find((word) =>
        word.startsWith(queryWord) || queryWord.startsWith(word)
      );
      if (fuzzyCandidate) {
        score += 1400;
        continue;
      }

      const bestDistance = entry.words.reduce((best, word) => {
        return Math.min(best, levenshteinDistance(queryWord, word));
      }, Number.POSITIVE_INFINITY);

      const maxAllowedDistance = Math.max(1, Math.ceil(queryWord.length * 0.25));
      if (bestDistance <= maxAllowedDistance && queryWord.length >= 3) {
        score += 800;
      }
    }

    if (queryWords.length > 1 && allWordsMatched) {
      score += 1200;
    }

    return score > 0 ? score - Math.max(0, target.length - query.length) * 2 : 0;
  }

  function searchProductsByName(products, query) {
    const normalizedQuery = normalizeProductSearchText(query);
    if (!normalizedQuery) {
      return products;
    }

    const searchableProducts = getProductSearchIndex(products);
    return searchableProducts
      .map((entry) => ({
        product: entry.product,
        score: scoreProductNameMatch(entry, normalizedQuery),
      }))
      .filter((item) => item.score > 0)
      .sort((left, right) => {
        if (right.score !== left.score) return right.score - left.score;
        return String(left.product.name).localeCompare(String(right.product.name));
      })
      .map((item) => item.product);
  }

  async function loadCategories() {
    const categoryFilter = document.querySelector("#category-filter");
    if (!categoryFilter) return;

    const currentValue = categoryFilter.value;

    try {
      const categories = await fetchCategories();
      categoryFilter.innerHTML = `
        <option value="">All products</option>
        ${categories.map((category) => `<option value="${category}">${category}</option>`).join("")}
      `;
      if (currentValue && categories.includes(currentValue)) {
        categoryFilter.value = currentValue;
      }
    } catch (error) {
      categoryFilter.innerHTML = `<option value="">All products</option>`;
      if (currentValue) {
        categoryFilter.value = "";
      }
      showToast("Unable to load categories", "error");
    }
  }

  async function renderProducts() {
    const grid = document.querySelector("[data-product-grid]");
    if (!grid) return;

    try {
      const allProducts = await fetchProducts();
      const categoryFilter = document.querySelector("#category-filter");
      const searchInput = document.querySelector("#product-search");
      const selectedCategory = categoryFilter ? categoryFilter.value : "";
      const searchTerm = searchInput ? normalizeProductSearchText(searchInput.value) : "";

      const filteredProducts = searchProductsByName(allProducts, searchTerm)
        .filter((product) => !selectedCategory || product.category === selectedCategory);

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

  const searchToggle = document.querySelector("[data-search-toggle]");
  const searchPanel = document.querySelector("[data-search-panel]");
  const searchForm = document.querySelector("[data-search-form]");
  const searchInput = document.querySelector("#product-search");

  if (searchToggle && searchPanel && searchForm && searchInput) {
    searchToggle.addEventListener("click", () => {
      const isOpen = searchPanel.classList.toggle("is-open");
      searchToggle.setAttribute("aria-expanded", String(isOpen));
      searchForm.classList.toggle("is-open", isOpen);
      if (isOpen) {
        searchInput.focus();
      } else {
        searchInput.value = "";
        renderProducts();
      }
    });

    searchInput.addEventListener("input", () => {
      renderProducts();
    });

    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      renderProducts();
    });
  }

  async function refreshCatalogViews() {
    loadCategories();
    renderProducts();
    renderProductDetails();
  }

  const catalogChannel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("catalog-updates") : null;
  if (catalogChannel) {
    catalogChannel.onmessage = (event) => {
      if (event.data && event.data.type === "catalog-updated") {
        refreshCatalogViews();
      }
    };
  }

  window.addEventListener("storage", (event) => {
    if (event.key === "catalog_updated_at") {
      refreshCatalogViews();
    }
  });

  window.addEventListener("focus", () => {
    if (document.visibilityState === "visible") {
      renderProducts();
      renderProductDetails();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      renderProducts();
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
