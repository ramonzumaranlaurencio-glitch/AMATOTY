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

  const TRUSTED_IMAGE_PATTERNS = [
    "mlstatic.com",
    "m.media-amazon.com",
    "alicdn.com",
    "ae01.alicdn.com"
  ];

  const TRUSTED_IMAGE_SOURCES = [
    "marketplace_thumbnail",
    "mercadolibre",
    "amazon",
    "aliexpress",
    "official"
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
    const url = String(product.image || "").trim();
    const urlLower = url.toLowerCase();
    if (!url) return false;
    if (BAD_IMAGE_PATTERNS.some((bad) => urlLower.includes(String(bad).toLowerCase()))) return false;
    const score = Number(product.image_match_score || 0);
    const source = String(product.image_source || product.source || "").toLowerCase();
    const trustedSource = TRUSTED_IMAGE_SOURCES.some((item) => source.includes(item));
    const trustedUrl = TRUSTED_IMAGE_PATTERNS.some((item) => urlLower.includes(item));
    if (product.image_verified === true && (trustedSource || trustedUrl) && score >= 0.72) return true;
    return product.image_verified === true && score >= 0.82;
  }

  function productImage(product, prefix) {
    return imageIsAllowed(product) ? product.image : fallbackFor(product, prefix);
  }

  function productCard(product, options) {
    const opts = options || {};
    product = flattenProduct(product);
    const prefix = opts.prefix || "";
    const image = productImage(product, prefix);
    const name = escapeHtml(product.name);
    const brand = escapeHtml(product.brand);
    const category = escapeHtml(product.category);
    const cta = escapeHtml(product.cta || "Ver opciones");
    const query = encodeURIComponent(product.search_query || product.name || "");
    const firstSource = Array.isArray(product.source_links) && product.source_links.length ? product.source_links[0].url : "";
    const href = product.product_url || firstSource || "smart-search.html";
    const target = /^https?:\/\//i.test(href) ? ' target="_blank" rel="nofollow noopener"' : "";
    const sourceNote = imageIsAllowed(product)
      ? (String(product.image_source || "").includes("marketplace") ? "Imagen de marketplace" : "Imagen verificada por IA")
      : "Imagen referencial: pendiente de verificacion IA";

    return `
      <div class="card" style="background:#fff;min-width:220px;max-width:320px;margin:12px auto;padding:18px;box-shadow:0 2px 12px #d5d9d9;">
        <img src="${escapeHtml(image)}" alt="${name}" style="width:100%;height:180px;object-fit:cover;border-radius:12px;margin-bottom:8px;">
        <h3 style="color:#b12704;">${name}</h3>
        <div style="font-size:0.95em;color:#64748b;margin-bottom:6px;">${brand ? brand + " - " : ""}${category}</div>
        <p style="font-size:1.05em;margin-bottom:8px;">${escapeHtml(product.short_desc)}</p>
        <ul style="font-size:0.97em;color:#334155;margin-bottom:8px;">
          <li><b>Problema:</b> ${escapeHtml(product.problem)}</li>
          <li><b>Publico:</b> ${escapeHtml(product.target)}</li>
          <li><b>Specs:</b> ${escapeHtml(product.specs || "")}</li>
        </ul>
        <a href="${escapeHtml(href)}"${target} style="display:inline-block;background:linear-gradient(180deg,#ffd814,#f7ca00);color:#111;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:bold;border:1px solid #fcd200;box-shadow:0 2px 5px rgba(213,217,217,.5);">${cta}</a>
        <div style="font-size:0.9em;color:#64748b;margin-top:8px;">${sourceNote}</div>
        <div style="font-size:0.93em;color:#0e7490;margin-top:6px;">${escapeHtml(product.reason)}</div>
        <div style="font-size:0.93em;color:#0369a1;margin-top:4px;">${escapeHtml(product.hook)}</div>
      </div>
    `;
  }

  function flattenProduct(product) {
    const principal = product.producto_principal || {};
    const sales = product.panel_de_ventas || {};
    const publish = product.publicacion || {};
    const specs = product.especificaciones_dinamicas || [];
    return Object.assign({}, product, {
      name: product.name || principal.nombre_generico || publish.titulo_seo || "Producto detectado",
      brand: product.brand || principal.marca || "",
      category: product.category || product.categoria_maestra || product.industria_detectada || "Otros",
      short_desc: product.short_desc || publish.descripcion_corta || principal.descripcion_visual || "",
      problem: product.problem || sales.beneficio_principal || "Necesidad por confirmar",
      target: product.target || "Publico por validar",
      specs: product.specs || specs.map((item) => `${item.etiqueta}: ${item.valor}`).join(", "),
      cta: product.cta || "Ver opciones",
      reason: product.reason || sales.mejor_opcion_argumento || "",
      hook: product.hook || sales.recomendacion_cross_selling || "",
      search_query: product.search_query || publish.search_query || principal.nombre_generico || "",
      image_verified: product.image_verified ?? publish.image_verified,
      image_match_score: product.image_match_score ?? publish.image_match_score
    });
  }

  function extractProducts(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.products)) return payload.products;
    if (Array.isArray(payload.productos)) return payload.productos;
    const universal = payload.deteccion_universal || {};
    if (Array.isArray(universal.productos)) return universal.productos.map(flattenProduct);
    return [];
  }

  function renderProductGrid(containerId, products, options) {
    const container = document.getElementById(containerId);
    if (!container) return;
    products = extractProducts(products);
    if (!products.length) {
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
    extractProducts,
    flattenProduct,
    productCard,
    productImage,
    renderProductGrid,
    renderProRecommendation
  };
})();
