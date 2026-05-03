(function () {
  const LOCAL_API_ORIGIN = "http://127.0.0.1:5050";

  function apiOrigin() {
    const host = window.location.hostname;
    const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(host);
    if (window.location.protocol === "file:") return LOCAL_API_ORIGIN;
    if (host.includes("github.io")) return "https://amatoty.onrender.com";
    if (isLocalHost && window.location.port && window.location.port !== "5050") return LOCAL_API_ORIGIN;
    return "";
  }

  function extractProducts(payload) {
    if (window.ProductAIGuard) return window.ProductAIGuard.extractProducts(payload);
    if (Array.isArray(payload)) return payload;
    return payload?.products || [];
  }

  function productKey(product) {
    return [product?.name, product?.brand, product?.category, product?.sku]
      .filter(Boolean)
      .join("|")
      .toLowerCase();
  }

  function mergeProducts(primary, fallback) {
    const seen = new Set();
    return [...(primary || []), ...(fallback || [])].filter((product) => {
      const key = productKey(product);
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  async function fetchJson(url) {
    const response = await fetch(url, {cache: "no-store"});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  async function fetchPlatformProducts(params) {
    const query = new URLSearchParams(params || {});
    const suffix = query.toString() ? `?${query}` : "";
    const payload = await fetchJson(`${apiOrigin()}/api/platform/public-products${suffix}`);
    return extractProducts(payload);
  }

  async function loadMergedProducts(fallbackUrl, params) {
    let fallbackProducts = [];
    let platformProducts = [];
    try {
      fallbackProducts = extractProducts(await fetchJson(fallbackUrl));
    } catch (_) {
      fallbackProducts = [];
    }
    try {
      platformProducts = await fetchPlatformProducts(params);
    } catch (_) {
      platformProducts = [];
    }
    return mergeProducts(platformProducts, fallbackProducts);
  }

  function renderComparison(products) {
    const table = document.querySelector(".comparador");
    if (!table || !products.length) return;
    const rows = products.slice(0, 5).map((product, index) => `
      <tr class="${index === 0 ? "highlight" : ""}">
        <td>${ProductAIGuard.escapeHtml(product.name || "")}</td>
        <td>${ProductAIGuard.escapeHtml(product.target || product.organization_name || "Clientes")}</td>
        <td>${ProductAIGuard.escapeHtml(product.problem || product.category || "Producto publicado")}</td>
        <td>${ProductAIGuard.escapeHtml(product.currency || "USD")} ${Number(product.price_sale || product.price_base || 0).toLocaleString()}</td>
      </tr>
    `).join("");
    table.innerHTML = `<tr><th>Producto</th><th>Mejor para</th><th>Problema</th><th>Precio</th></tr>${rows}`;
  }

  async function hydrateHome(options) {
    const opts = options || {};
    const products = await loadMergedProducts(opts.fallbackUrl || "assets/trending_products.json", {limit: opts.limit || 24});
    if (window.ProductAIGuard) {
      ProductAIGuard.renderProductGrid("top-picks-list", products);
      ProductAIGuard.renderProRecommendation("pro-recommendation", products[0]);
      ProductAIGuard.renderProductGrid("product-gallery", products);
    }
    renderComparison(products);
    return products;
  }

  window.PlatformCatalog = {
    apiOrigin,
    fetchPlatformProducts,
    loadMergedProducts,
    hydrateHome,
    mergeProducts
  };
})();
