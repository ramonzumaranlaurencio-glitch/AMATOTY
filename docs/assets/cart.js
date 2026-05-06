/**
 * cart.js — Global cart for the LCA PRO platform.
 *
 * Drop this script on ANY page that needs cart / checkout functionality.
 * It uses localStorage so the cart persists across pages (same origin).
 *
 * Public API (window.LCACart):
 *   LCACart.add(product)          — add or increment a product
 *   LCACart.remove(productId)     — remove a product completely
 *   LCACart.setQty(productId, n)  — set exact quantity
 *   LCACart.clear()               — empty the cart
 *   LCACart.get()                 — return current cart array
 *   LCACart.count()               — total item count
 *   LCACart.total()               — grand total (number)
 *   LCACart.openDrawer()          — open the cart drawer
 *   LCACart.closeDrawer()         — close the cart drawer
 *   LCACart.renderProductCard(p)  — returns HTML string for a product card
 *   LCACart.openCheckout()        — open the checkout modal
 */

(function () {
  "use strict";

  // ── Storage ──────────────────────────────────────────────────────────────
  const STORAGE_KEY = "lca_cart_v1";

  function loadCart() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveCart(cart) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    _emit("lca:cart:updated", { cart });
  }

  function _emit(name, detail) {
    document.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
  }

  // ── Core Operations ───────────────────────────────────────────────────────
  const Cart = {
    get() {
      return loadCart();
    },

    count() {
      return loadCart().reduce((s, i) => s + i.quantity, 0);
    },

    total() {
      return loadCart().reduce((s, i) => s + i.unit_price * i.quantity, 0);
    },

    /**
     * product shape:
     * { id, product_id, name, unit_price, currency, quantity, sku, image }
     */
    add(product) {
      const cart = loadCart();
      const pid = String(product.product_id || product.id || "");
      const qty = Math.max(1, parseInt(product.quantity, 10) || 1);
      const idx = cart.findIndex((i) => i.product_id === pid);
      if (idx >= 0) {
        cart[idx].quantity += qty;
      } else {
        cart.push({
          product_id: pid,
          name: String(product.name || "Product"),
          unit_price: parseFloat(product.unit_price || product.price_sale || product.price || 0),
          currency: String(product.currency || "USD"),
          quantity: qty,
          sku: String(product.sku || ""),
          image: String(product.image || ""),
        });
      }
      saveCart(cart);
      _showToast(`✓ "${product.name}" added to cart`);
      _updateBadge();
    },

    remove(productId) {
      const pid = String(productId);
      saveCart(loadCart().filter((i) => i.product_id !== pid));
      _updateBadge();
      _renderDrawer();
    },

    setQty(productId, qty) {
      const pid = String(productId);
      qty = parseInt(qty, 10);
      if (qty <= 0) return Cart.remove(pid);
      const cart = loadCart();
      const idx = cart.findIndex((i) => i.product_id === pid);
      if (idx >= 0) {
        cart[idx].quantity = qty;
        saveCart(cart);
        _updateBadge();
        _renderDrawer();
      }
    },

    clear() {
      saveCart([]);
      _updateBadge();
      _renderDrawer();
    },

    openDrawer() {
      _ensureUI();
      _renderDrawer();
      document.getElementById("lca-cart-drawer").classList.add("open");
      document.getElementById("lca-cart-overlay").classList.add("visible");
    },

    closeDrawer() {
      const d = document.getElementById("lca-cart-drawer");
      const o = document.getElementById("lca-cart-overlay");
      if (d) d.classList.remove("open");
      if (o) o.classList.remove("visible");
    },

    openCheckout() {
      Cart.closeDrawer();
      _ensureCheckoutModal();
      _renderCheckoutModal();
      document.getElementById("lca-checkout-modal").classList.add("open");
    },

    /** Returns an HTML string for a product card with cart controls */
    renderProductCard(p) {
      const pid = p.product_id || p.id || "";
      const price = parseFloat(p.price_sale || p.unit_price || p.price || 0);
      const currency = p.currency || "USD";
      const img = p.image
        ? `<img src="${_esc(p.image)}" alt="${_esc(p.name)}" class="lca-card-img" onerror="this.style.display='none'">`
        : `<div class="lca-card-img-placeholder">📦</div>`;
      return `
<div class="lca-product-card" data-pid="${_esc(pid)}">
  ${img}
  <div class="lca-card-body">
    <div class="lca-card-name">${_esc(p.name)}</div>
    <div class="lca-card-brand">${_esc(p.brand || "")}</div>
    <div class="lca-card-price">${currency} ${price.toFixed(2)}</div>
    <div class="lca-card-qty-row">
      <button class="lca-qty-btn" onclick="window.LCACart._dec('${_esc(pid)}',this)">−</button>
      <input class="lca-qty-input" type="number" min="1" value="1"
             onchange="window.LCACart._setInput('${_esc(pid)}',this)" />
      <button class="lca-qty-btn" onclick="window.LCACart._inc('${_esc(pid)}',this)">+</button>
    </div>
    <div class="lca-card-actions">
      <button class="lca-btn-cart"
        onclick="window.LCACart._addFromCard('${_esc(pid)}',this,${JSON.stringify(_esc(p.name))},${price},'${_esc(currency)}','${_esc(p.sku||'')}','${_esc(p.image||'')}')">
        Add to cart
      </button>
      <button class="lca-btn-buy"
        onclick="window.LCACart._buyNow('${_esc(pid)}',this,${JSON.stringify(_esc(p.name))},${price},'${_esc(currency)}','${_esc(p.sku||'')}','${_esc(p.image||'')}')">
        Buy now
      </button>
    </div>
  </div>
</div>`;
    },

    // ── Internal helpers exposed for inline onclick ──────────────────────
    _dec(pid, btn) {
      const input = btn.parentElement.querySelector(".lca-qty-input");
      input.value = Math.max(1, parseInt(input.value, 10) - 1);
    },
    _inc(pid, btn) {
      const input = btn.parentElement.querySelector(".lca-qty-input");
      input.value = parseInt(input.value, 10) + 1;
    },
    _setInput(pid, input) {
      input.value = Math.max(1, parseInt(input.value, 10) || 1);
    },
    _addFromCard(pid, btn, name, price, currency, sku, image) {
      const qty = parseInt(btn.closest(".lca-product-card").querySelector(".lca-qty-input").value, 10) || 1;
      Cart.add({ product_id: pid, name, unit_price: price, currency, quantity: qty, sku, image });
    },
    _buyNow(pid, btn, name, price, currency, sku, image) {
      const qty = parseInt(btn.closest(".lca-product-card").querySelector(".lca-qty-input").value, 10) || 1;
      Cart.add({ product_id: pid, name, unit_price: price, currency, quantity: qty, sku, image });
      Cart.openCheckout();
    },
  };

  // ── Badge ─────────────────────────────────────────────────────────────────
  function _updateBadge() {
    const n = Cart.count();
    document.querySelectorAll(".lca-cart-badge").forEach((el) => {
      el.textContent = n;
      el.style.display = n > 0 ? "inline-flex" : "none";
    });
  }

  // ── Toast ─────────────────────────────────────────────────────────────────
  function _showToast(msg) {
    let t = document.getElementById("lca-cart-toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "lca-cart-toast";
      t.style.cssText =
        "position:fixed;bottom:24px;right:24px;background:#1a1a2e;color:#fff;" +
        "padding:12px 20px;border-radius:8px;font-size:14px;z-index:99999;" +
        "box-shadow:0 4px 16px rgba(0,0,0,.3);transition:opacity .3s;opacity:0;pointer-events:none";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = "1";
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.style.opacity = "0"; }, 2600);
  }

  // ── Cart Drawer ───────────────────────────────────────────────────────────
  function _ensureUI() {
    if (document.getElementById("lca-cart-drawer")) return;

    // Inject styles
    const style = document.createElement("style");
    style.textContent = `
      #lca-cart-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9998;opacity:0;pointer-events:none;transition:opacity .25s}
      #lca-cart-overlay.visible{opacity:1;pointer-events:auto}
      #lca-cart-drawer{position:fixed;top:0;right:-420px;width:min(420px,100vw);height:100%;background:#fff;z-index:9999;display:flex;flex-direction:column;box-shadow:-4px 0 24px rgba(0,0,0,.18);transition:right .28s cubic-bezier(.4,0,.2,1)}
      #lca-cart-drawer.open{right:0}
      .lca-drawer-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #e8e8e8;font-weight:700;font-size:18px}
      .lca-drawer-close{background:none;border:none;font-size:24px;cursor:pointer;line-height:1;color:#555}
      .lca-drawer-items{flex:1;overflow-y:auto;padding:12px 16px}
      .lca-drawer-empty{text-align:center;color:#999;padding:48px 16px;font-size:15px}
      .lca-drawer-item{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #f0f0f0}
      .lca-drawer-item-img{width:56px;height:56px;object-fit:cover;border-radius:6px;flex-shrink:0;background:#f5f5f5}
      .lca-drawer-item-info{flex:1;min-width:0}
      .lca-drawer-item-name{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .lca-drawer-item-price{font-size:13px;color:#555;margin-top:2px}
      .lca-drawer-item-controls{display:flex;align-items:center;gap:6px;margin-top:6px}
      .lca-drawer-qty-btn{width:26px;height:26px;border:1px solid #ddd;border-radius:4px;background:#f8f8f8;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}
      .lca-drawer-qty{font-size:14px;min-width:24px;text-align:center}
      .lca-drawer-remove{margin-left:auto;background:none;border:none;color:#c00;cursor:pointer;font-size:13px}
      .lca-drawer-footer{padding:16px 20px;border-top:1px solid #e8e8e8}
      .lca-drawer-total{display:flex;justify-content:space-between;font-weight:700;font-size:17px;margin-bottom:14px}
      .lca-btn-checkout{width:100%;padding:14px;background:#6c63ff;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer}
      .lca-btn-checkout:hover{background:#574fd6}
      .lca-btn-clear{width:100%;padding:8px;background:none;border:1px solid #ddd;border-radius:6px;font-size:13px;color:#888;cursor:pointer;margin-top:8px}
      /* Checkout modal */
      #lca-checkout-modal{position:fixed;inset:0;z-index:10000;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.55)}
      #lca-checkout-modal.open{display:flex}
      .lca-checkout-box{background:#fff;border-radius:12px;width:min(560px,96vw);max-height:90vh;overflow-y:auto;padding:28px 28px 20px;box-shadow:0 8px 40px rgba(0,0,0,.22)}
      .lca-checkout-title{font-size:20px;font-weight:700;margin-bottom:16px}
      .lca-checkout-summary{margin-bottom:18px;border:1px solid #eee;border-radius:8px;padding:12px 16px}
      .lca-checkout-row{display:flex;justify-content:space-between;font-size:14px;padding:4px 0}
      .lca-checkout-total{font-weight:700;font-size:17px;border-top:1px solid #eee;margin-top:8px;padding-top:8px}
      .lca-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}
      .lca-form-full{grid-column:1/-1}
      .lca-form-grid input{padding:9px 12px;border:1px solid #d0d0d0;border-radius:6px;font-size:14px;width:100%;box-sizing:border-box}
      .lca-form-grid input:focus{outline:none;border-color:#6c63ff}
      .lca-btn-pay{width:100%;padding:15px;background:#6c63ff;color:#fff;border:none;border-radius:8px;font-size:17px;font-weight:700;cursor:pointer;margin-top:6px}
      .lca-btn-pay:disabled{background:#aaa;cursor:not-allowed}
      .lca-btn-modal-close{float:right;background:none;border:none;font-size:22px;cursor:pointer;color:#888;margin-top:-4px}
      .lca-form-label{font-size:13px;color:#666;margin-bottom:2px;display:block}
      .lca-form-group{display:flex;flex-direction:column}
      /* Product card */
      .lca-product-card{border:1px solid #e8e8e8;border-radius:10px;overflow:hidden;background:#fff;display:flex;flex-direction:column;transition:box-shadow .2s}
      .lca-product-card:hover{box-shadow:0 4px 20px rgba(0,0,0,.1)}
      .lca-card-img{width:100%;height:180px;object-fit:cover}
      .lca-card-img-placeholder{width:100%;height:180px;display:flex;align-items:center;justify-content:center;background:#f5f5f5;font-size:48px}
      .lca-card-body{padding:14px}
      .lca-card-name{font-size:15px;font-weight:600;margin-bottom:2px}
      .lca-card-brand{font-size:12px;color:#888;margin-bottom:6px}
      .lca-card-price{font-size:18px;font-weight:700;color:#6c63ff;margin-bottom:10px}
      .lca-card-qty-row{display:flex;align-items:center;gap:8px;margin-bottom:10px}
      .lca-qty-btn{width:30px;height:30px;border:1px solid #ddd;border-radius:4px;background:#f5f5f5;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center}
      .lca-qty-input{width:50px;padding:4px;text-align:center;border:1px solid #ddd;border-radius:4px;font-size:15px}
      .lca-card-actions{display:flex;gap:8px}
      .lca-btn-cart{flex:1;padding:9px;border:2px solid #6c63ff;color:#6c63ff;background:#fff;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
      .lca-btn-cart:hover{background:#f0eeff}
      .lca-btn-buy{flex:1;padding:9px;background:#6c63ff;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
      .lca-btn-buy:hover{background:#574fd6}
    `;
    document.head.appendChild(style);

    // Overlay
    const overlay = document.createElement("div");
    overlay.id = "lca-cart-overlay";
    overlay.onclick = Cart.closeDrawer;
    document.body.appendChild(overlay);

    // Drawer
    const drawer = document.createElement("div");
    drawer.id = "lca-cart-drawer";
    drawer.innerHTML = `
      <div class="lca-drawer-header">
        <span>🛒 Cart</span>
        <button class="lca-drawer-close" onclick="window.LCACart.closeDrawer()">×</button>
      </div>
      <div class="lca-drawer-items" id="lca-drawer-items"></div>
      <div class="lca-drawer-footer">
        <div class="lca-drawer-total">
          <span>Total</span>
          <span id="lca-drawer-total-val">$0.00</span>
        </div>
        <button class="lca-btn-checkout" onclick="window.LCACart.openCheckout()">Proceed to checkout</button>
        <button class="lca-btn-clear" onclick="window.LCACart.clear()">Clear cart</button>
      </div>`;
    document.body.appendChild(drawer);
  }

  function _renderDrawer() {
    const itemsEl = document.getElementById("lca-drawer-items");
    const totalEl = document.getElementById("lca-drawer-total-val");
    if (!itemsEl) return;
    const cart = loadCart();
    if (!cart.length) {
      itemsEl.innerHTML = `<div class="lca-drawer-empty">Your cart is empty</div>`;
      if (totalEl) totalEl.textContent = "$0.00";
      return;
    }
    const currency = cart[0]?.currency || "USD";
    itemsEl.innerHTML = cart
      .map(
        (item) => `
      <div class="lca-drawer-item">
        ${item.image ? `<img class="lca-drawer-item-img" src="${_esc(item.image)}" alt="${_esc(item.name)}" onerror="this.style.display='none'">` : `<div class="lca-drawer-item-img" style="display:flex;align-items:center;justify-content:center;font-size:24px">📦</div>`}
        <div class="lca-drawer-item-info">
          <div class="lca-drawer-item-name">${_esc(item.name)}</div>
          <div class="lca-drawer-item-price">${currency} ${item.unit_price.toFixed(2)}</div>
          <div class="lca-drawer-item-controls">
            <button class="lca-drawer-qty-btn" onclick="window.LCACart.setQty('${_esc(item.product_id)}',${item.quantity - 1})">−</button>
            <span class="lca-drawer-qty">${item.quantity}</span>
            <button class="lca-drawer-qty-btn" onclick="window.LCACart.setQty('${_esc(item.product_id)}',${item.quantity + 1})">+</button>
            <button class="lca-drawer-remove" onclick="window.LCACart.remove('${_esc(item.product_id)}')">Remove</button>
          </div>
        </div>
      </div>`
      )
      .join("");
    if (totalEl) {
      const t = Cart.total();
      totalEl.textContent = `${currency} ${t.toFixed(2)}`;
    }
  }

  // ── Checkout Modal ────────────────────────────────────────────────────────
  function _ensureCheckoutModal() {
    if (document.getElementById("lca-checkout-modal")) return;
    const modal = document.createElement("div");
    modal.id = "lca-checkout-modal";
    document.body.appendChild(modal);
  }

  function _renderCheckoutModal() {
    const modal = document.getElementById("lca-checkout-modal");
    if (!modal) return;
    const cart = loadCart();
    const currency = cart[0]?.currency || "USD";
    const subtotal = Cart.total();
    const itemsHtml = cart
      .map(
        (item) =>
          `<div class="lca-checkout-row"><span>${_esc(item.name)} x${item.quantity}</span><span>${currency} ${(item.unit_price * item.quantity).toFixed(2)}</span></div>`
      )
      .join("");

    modal.innerHTML = `
      <div class="lca-checkout-box">
        <button class="lca-btn-modal-close" onclick="document.getElementById('lca-checkout-modal').classList.remove('open')">×</button>
        <div class="lca-checkout-title">Checkout</div>
        <div class="lca-checkout-summary">
          ${itemsHtml}
          <div class="lca-checkout-row lca-checkout-total"><span>Total</span><span>${currency} ${subtotal.toFixed(2)}</span></div>
        </div>
        <div class="lca-form-grid">
          <div class="lca-form-group lca-form-full"><label class="lca-form-label">Full name *</label><input id="lca-f-name" placeholder="John Doe"></div>
          <div class="lca-form-group"><label class="lca-form-label">Email *</label><input id="lca-f-email" type="email" placeholder="you@email.com"></div>
          <div class="lca-form-group"><label class="lca-form-label">Phone</label><input id="lca-f-phone" placeholder="+1 555 000 0000"></div>
          <div class="lca-form-group lca-form-full"><label class="lca-form-label">Address</label><input id="lca-f-address" placeholder="Street and number"></div>
          <div class="lca-form-group"><label class="lca-form-label">City</label><input id="lca-f-city" placeholder="Lima"></div>
          <div class="lca-form-group"><label class="lca-form-label">State / Region</label><input id="lca-f-state" placeholder="Lima"></div>
          <div class="lca-form-group"><label class="lca-form-label">ZIP / Postal code</label><input id="lca-f-zip" placeholder="15001"></div>
          <div class="lca-form-group"><label class="lca-form-label">Country</label><input id="lca-f-country" placeholder="PE" value="PE"></div>
        </div>
        <button class="lca-btn-pay" id="lca-pay-btn" onclick="window.LCACart._submitCheckout()">
          Pay ${currency} ${subtotal.toFixed(2)}
        </button>
        <div id="lca-checkout-error" style="color:#c00;font-size:13px;margin-top:10px;display:none"></div>
      </div>`;
  }

  // ── Submit Checkout ───────────────────────────────────────────────────────
  Cart._submitCheckout = async function () {
    const btn = document.getElementById("lca-pay-btn");
    const errEl = document.getElementById("lca-checkout-error");
    const v = (id) => (document.getElementById(id) || {}).value || "";

    const name = v("lca-f-name").trim();
    const email = v("lca-f-email").trim();
    if (!name || !email) {
      errEl.textContent = "Name and email are required.";
      errEl.style.display = "block";
      return;
    }
    errEl.style.display = "none";
    btn.disabled = true;
    btn.textContent = "Processing…";

    const cart = loadCart();
    const payload = {
      cart: cart.map((item) => ({
        product_id: item.product_id,
        name: item.name,
        unit_price: item.unit_price,
        quantity: item.quantity,
        currency: item.currency,
        sku: item.sku,
      })),
      customer: {
        name,
        email,
        phone: v("lca-f-phone"),
        address: v("lca-f-address"),
        city: v("lca-f-city"),
        state: v("lca-f-state"),
        zip: v("lca-f-zip"),
        country: v("lca-f-country"),
      },
      currency: cart[0]?.currency || "USD",
      shipping: 0,
      tax: 0,
    };

    try {
      const res = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Unknown error");

      // Redirect to SafePay checkout
      Cart.clear();
      window.location.href = data.checkout_url || data.pay_url;
    } catch (err) {
      errEl.textContent = `Payment error: ${err.message}`;
      errEl.style.display = "block";
      btn.disabled = false;
      btn.textContent = "Retry payment";
    }
  };

  // ── Utility ───────────────────────────────────────────────────────────────
  function _esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  function _boot() {
    _ensureUI();
    _updateBadge();
    // Keep badge in sync across tabs
    window.addEventListener("storage", (e) => {
      if (e.key === STORAGE_KEY) _updateBadge();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _boot);
  } else {
    _boot();
  }

  window.LCACart = Cart;
})();
