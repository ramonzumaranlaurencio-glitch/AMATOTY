(function () {
  const LOCAL_API_ORIGIN = "http://127.0.0.1:5050";
  const DEFAULT_FALLBACK = "assets/productos.json";
  const CSS_ID = "msn-banner-carousel-css";

  function apiOrigin() {
    const host = window.location.hostname;
    const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(host);
    if (window.location.protocol === "file:") return LOCAL_API_ORIGIN;
    if (host.includes("github.io")) return "https://amatoty.onrender.com";
    if (isLocalHost && window.location.port && window.location.port !== "5050") return LOCAL_API_ORIGIN;
    return "";
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, ch => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    })[ch]);
  }

  function boolValue(value) {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value !== 0;
    return ["1", "true", "yes", "si", "on"].includes(String(value || "").trim().toLowerCase());
  }

  function extractProducts(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.products)) return payload.products;
    if (Array.isArray(payload?.productos)) return payload.productos;
    if (Array.isArray(payload?.items)) return payload.items;
    return [];
  }

  async function fetchJson(url) {
    const response = await fetch(url, {cache: "no-store"});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  async function loadProducts(fallbackUrl, limit) {
    const products = [];
    try {
      const query = new URLSearchParams({limit: String(limit || 48)});
      products.push(...extractProducts(await fetchJson(`${apiOrigin()}/api/platform/public-products?${query}`)));
    } catch (_) {}
    try {
      products.push(...extractProducts(await fetchJson(fallbackUrl || DEFAULT_FALLBACK)));
    } catch (_) {}
    return dedupe(products);
  }

  function dedupe(products) {
    const seen = new Set();
    return (products || []).filter(product => {
      const key = [product.id, product.sku, product.name || product.nombre, product.banner_title || product.title || product.titulo]
        .filter(Boolean)
        .join("|")
        .toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function isFeatured(product) {
    const banner = product.banner || {};
    return boolValue(
      product.mostrar_en_banner ??
      product.show_in_banner ??
      product.destacado ??
      product.featured ??
      banner.show ??
      banner.mostrar
    );
  }

  function firstImage(product) {
    if (product.banner_image) return product.banner_image;
    if (product.banner?.image) return product.banner.image;
    if (product.image) return product.image;
    if (product.imagen) return product.imagen;
    if (product.imagen_ref) return product.imagen_ref;
    if (Array.isArray(product.imagenes) && product.imagenes[0]) return product.imagenes[0];
    if (Array.isArray(product.images) && product.images[0]) return product.images[0];
    if (Array.isArray(product.media)) {
      const image = product.media.find(item => item.media_type === "image" && item.url);
      if (image) return image.url;
    }
    return "assets/home.jpg";
  }

  function normalize(product) {
    const banner = product.banner || {};
    const title = banner.title || product.banner_title || product.titulo || product.title || product.name || product.nombre || "Producto destacado";
    const description = banner.description || product.banner_description || product.descripcion_corta || product.short_desc || product.description || product.desc || "";
    const link = banner.link || product.banner_link || product.enlace_boton || product.product_url || product.url || "product-platform.html";
    const buttonText = banner.button_text || product.banner_button_text || product.texto_boton || product.cta || "Ver producto";
    const category = banner.category || product.banner_category || product.category || product.categoria || "";
    return {
      title,
      description,
      image: firstImage(product),
      link,
      buttonText,
      category
    };
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    const style = document.createElement("style");
    style.id = CSS_ID;
    style.textContent = `
      .msn-carousel{position:relative;overflow:hidden;border-radius:8px;min-height:360px;background:#111827;color:#fff;box-shadow:0 14px 34px rgba(15,23,42,.18);margin:0 0 22px}
      .msn-carousel-track{display:flex;height:100%;transition:transform .48s ease}
      .msn-carousel-slide{min-width:100%;position:relative;min-height:360px;display:grid;align-items:end}
      .msn-carousel-slide img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
      .msn-carousel-slide:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(2,6,23,.82),rgba(2,6,23,.46) 48%,rgba(2,6,23,.12)),linear-gradient(0deg,rgba(2,6,23,.78),rgba(2,6,23,.1) 55%)}
      .msn-carousel-copy{position:relative;z-index:1;max-width:720px;padding:44px 56px 48px}
      .msn-carousel-kicker{display:inline-flex;align-items:center;min-height:24px;border:1px solid rgba(255,255,255,.42);border-radius:999px;padding:3px 10px;margin-bottom:12px;font-size:12px;font-weight:800;text-transform:uppercase;background:rgba(255,255,255,.12)}
      .msn-carousel-title{font-size:clamp(28px,4.5vw,54px);line-height:1.02;margin:0 0 12px;font-weight:900;letter-spacing:0}
      .msn-carousel-desc{font-size:17px;line-height:1.45;margin:0 0 18px;max-width:620px;color:#f8fafc}
      .msn-carousel-cta{display:inline-flex;align-items:center;justify-content:center;min-height:42px;background:#ff9900;color:#111827;border-radius:6px;padding:10px 16px;text-decoration:none;font-weight:900;box-shadow:0 8px 18px rgba(255,153,0,.32)}
      .msn-carousel-arrow{position:absolute;z-index:2;top:50%;transform:translateY(-50%);width:42px;height:42px;border:1px solid rgba(255,255,255,.5);border-radius:50%;background:rgba(15,23,42,.58);color:#fff;font-size:28px;line-height:1;display:grid;place-items:center;cursor:pointer}
      .msn-carousel-arrow:hover,.msn-carousel-arrow:focus{background:rgba(255,153,0,.96);color:#111827;outline:0}
      .msn-carousel-prev{left:14px}.msn-carousel-next{right:14px}
      .msn-carousel-dots{position:absolute;z-index:2;left:0;right:0;bottom:14px;display:flex;justify-content:center;gap:8px}
      .msn-carousel-dot{width:10px;height:10px;border-radius:50%;border:0;background:rgba(255,255,255,.52);padding:0;cursor:pointer}
      .msn-carousel-dot.active{background:#ff9900;box-shadow:0 0 0 4px rgba(255,153,0,.22)}
      @media(max-width:720px){
        .msn-carousel,.msn-carousel-slide{min-height:420px}
        .msn-carousel-copy{padding:76px 20px 54px}
        .msn-carousel-desc{font-size:15px}
        .msn-carousel-arrow{top:22px;transform:none;width:38px;height:38px}
        .msn-carousel-prev{left:auto;right:62px}.msn-carousel-next{right:16px}
      }
    `;
    document.head.appendChild(style);
  }

  function render(host, slides, options) {
    if (!slides.length) {
      host.hidden = true;
      return null;
    }
    host.hidden = false;
    host.innerHTML = `
      <section class="msn-carousel" aria-roledescription="carousel">
        <div class="msn-carousel-track">
          ${slides.map(slide => `
            <article class="msn-carousel-slide">
              <img src="${escapeHtml(slide.image)}" alt="${escapeHtml(slide.title)}" loading="lazy">
              <div class="msn-carousel-copy">
                ${slide.category ? `<span class="msn-carousel-kicker">${escapeHtml(slide.category)}</span>` : ""}
                <h2 class="msn-carousel-title">${escapeHtml(slide.title)}</h2>
                ${slide.description ? `<p class="msn-carousel-desc">${escapeHtml(slide.description)}</p>` : ""}
                <a class="msn-carousel-cta" href="${escapeHtml(slide.link)}">${escapeHtml(slide.buttonText)}</a>
              </div>
            </article>
          `).join("")}
        </div>
        <button class="msn-carousel-arrow msn-carousel-prev" type="button" aria-label="Anterior">&lt;</button>
        <button class="msn-carousel-arrow msn-carousel-next" type="button" aria-label="Siguiente">&gt;</button>
        <div class="msn-carousel-dots">
          ${slides.map((_, index) => `<button class="msn-carousel-dot${index === 0 ? " active" : ""}" type="button" aria-label="Ir al slide ${index + 1}"></button>`).join("")}
        </div>
      </section>
    `;
    return wire(host, slides.length, options);
  }

  function wire(host, total, options) {
    const track = host.querySelector(".msn-carousel-track");
    const dots = Array.from(host.querySelectorAll(".msn-carousel-dot"));
    const prev = host.querySelector(".msn-carousel-prev");
    const next = host.querySelector(".msn-carousel-next");
    let index = 0;
    let timer = null;

    function go(nextIndex) {
      index = (nextIndex + total) % total;
      track.style.transform = `translateX(-${index * 100}%)`;
      dots.forEach((dot, dotIndex) => dot.classList.toggle("active", dotIndex === index));
    }

    function stop() {
      if (timer) clearInterval(timer);
      timer = null;
    }

    function start() {
      stop();
      const interval = Number(options.interval || 6500);
      if (total > 1 && interval > 0) timer = setInterval(() => go(index + 1), interval);
    }

    prev.addEventListener("click", () => { go(index - 1); start(); });
    next.addEventListener("click", () => { go(index + 1); start(); });
    dots.forEach((dot, dotIndex) => dot.addEventListener("click", () => { go(dotIndex); start(); }));
    host.addEventListener("mouseenter", stop);
    host.addEventListener("mouseleave", start);
    start();
    return {go, stop, start};
  }

  async function mount(target, options) {
    const host = typeof target === "string" ? document.getElementById(target) : target;
    if (!host) return null;
    injectCss();
    const opts = options || {};
    const products = await loadProducts(opts.fallbackUrl || host.dataset.bannerFallback || DEFAULT_FALLBACK, opts.limit || host.dataset.bannerLimit || 48);
    const slides = products.filter(isFeatured).map(normalize).slice(0, Number(opts.maxSlides || host.dataset.bannerMax || 8));
    return render(host, slides, opts);
  }

  function autoMount() {
    document.querySelectorAll("[data-banner-carousel]").forEach(node => {
      mount(node).catch(() => { node.hidden = true; });
    });
  }

  window.BannerCarousel = {mount};
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount);
  } else {
    autoMount();
  }
})();
