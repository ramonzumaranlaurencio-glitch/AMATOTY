(function () {
  const CATEGORY_FALLBACKS = {
    belleza: "assets/home.jpg",
    cocina: "assets/kitchen.jpg",
    kitchen: "assets/kitchen.jpg",
    hogar: "assets/home.jpg",
    home: "assets/home.jpg",
    automocion: "assets/car.jpg",
    automotive: "assets/car.jpg",
    auto: "assets/car.jpg",
    default: "assets/home.jpg"
  };

  const BAD_IMAGE_PATTERNS = [
    "source.unsplash.com",
    "picsum.photos",
    "placeholder",
    "61Qe0euJJZL",
    "71Qe0euJJZL",
    "81Qe0euJJZL"
  ];

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function normalizeCategory(category) {
    return String(category || "default")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function fallbackFor(product, prefix) {
    const key = normalizeCategory(product.category);
    const file = CATEGORY_FALLBACKS[key] || CATEGORY_FALLBACKS.default;
    return prefix ? file.replace("assets/", prefix + "assets/") : file;
  }

  function imageIsAllowed(product) {
    const url = String(product.image || "");
    if (!url) return false;
    if (BAD_IMAGE_PATTERNS.some((bad) => url.includes(bad))) return false;
    return product.image_verified === true && Number(product.image_match_score || 0) >= 0.82;
  }

  function productImage(product, prefix) {
    return imageIsAllowed(product) ? product.image : fallbackFor(product, prefix);
  }

  function productCard(product, options) {
    const opts = options || {};
    const prefix = opts.prefix || "";
    const image = productImage(product, prefix);
    const name = escapeHtml(product.name);
    const brand = escapeHtml(product.brand);
    const category = escapeHtml(product.category);
    const cta = escapeHtml(product.cta || "Ver opciones");
    const query = encodeURIComponent(product.search_query || product.name || "");
    const sourceNote = imageIsAllowed(product)
      ? "Imagen verificada por IA"
      : "Imagen referencial: pendiente de verificacion IA";

    return `
      <div class="card" style="background:#fff;min-width:220px;max-width:320px;margin:12px auto;padding:18px;box-shadow:0 2px 12px #e2e8f0;">
        <img src="${escapeHtml(image)}" alt="${name}" style="width:100%;height:180px;object-fit:cover;border-radius:12px;margin-bottom:8px;">
        <h3 style="color:#0a6ed1;">${name}</h3>
        <div style="font-size:0.95em;color:#64748b;margin-bottom:6px;">${brand ? brand + " - " : ""}${category}</div>
        <p style="font-size:1.05em;margin-bottom:8px;">${escapeHtml(product.short_desc)}</p>
        <ul style="font-size:0.97em;color:#334155;margin-bottom:8px;">
          <li><b>Problema:</b> ${escapeHtml(product.problem)}</li>
          <li><b>Publico:</b> ${escapeHtml(product.target)}</li>
          <li><b>Specs:</b> ${escapeHtml(product.specs || "")}</li>
        </ul>
        <a href="https://www.amazon.com/s?k=${query}" target="_blank" rel="nofollow noopener" style="display:inline-block;background:#0a6ed1;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:bold;box-shadow:0 2px 8px #bae6fd;">${cta}</a>
        <div style="font-size:0.9em;color:#64748b;margin-top:8px;">${sourceNote}</div>
        <div style="font-size:0.93em;color:#0e7490;margin-top:6px;">${escapeHtml(product.reason)}</div>
        <div style="font-size:0.93em;color:#0369a1;margin-top:4px;">${escapeHtml(product.hook)}</div>
      </div>
    `;
  }

  function renderProductGrid(containerId, products, options) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!products || !products.length) {
      container.innerHTML = "<p>No hay productos tendencia hoy.</p>";
      return;
    }
    container.innerHTML = products.map((product) => productCard(product, options)).join("");
  }

  function renderProRecommendation(containerId, product, options) {
    const container = document.getElementById(containerId);
    if (!container || !product) return;
    container.innerHTML = productCard(product, options);
  }

  window.ProductAIGuard = {
    escapeHtml,
    imageIsAllowed,
    productCard,
    productImage,
    renderProductGrid,
    renderProRecommendation
  };
})();
