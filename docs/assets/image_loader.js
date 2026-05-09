/**
 * image_loader.js – Resilient product image system for AMATOTY
 *
 * Features:
 *  - Skeleton shimmer animation while images load
 *  - Multi-tier fallback chain: primary → category asset → SVG placeholder
 *  - Automatic broken-URL logging (console.warn)
 *  - IntersectionObserver lazy loading
 *  - object-fit: cover enforced via JS for legacy browsers
 *  - Prevents gray empty cards when external CDN images fail
 *
 * Usage:
 *  <img data-src="https://..." data-category="kitchen" data-fallback="assets/kitchen.jpg" class="lca-img" alt="...">
 *  LcaImageLoader.init();          // call once on DOMContentLoaded
 *  LcaImageLoader.upgrade(el);     // upgrade a specific container
 */
(function (root) {
  "use strict";

  // ── Category → local asset mapping ────────────────────────────────────────
  var CATEGORY_ASSETS = {
    // Kitchen / food
    kitchen:   "assets/kitchen.jpg",
    cocina:    "assets/kitchen.jpg",
    alimentos: "assets/kitchen.jpg",
    food:      "assets/kitchen.jpg",
    blender:   "assets/kitchen.jpg",
    "food saver": "assets/kitchen.jpg",
    "air fryer":  "assets/kitchen.jpg",
    // Home / hogar
    home:        "assets/home.jpg",
    hogar:       "assets/home.jpg",
    bedroom:     "assets/home.jpg",
    cleaning:    "assets/home.jpg",
    organizer:   "assets/home.jpg",
    "smart plug": "assets/home.jpg",
    vacuum:      "assets/home.jpg",
    blanket:     "assets/home.jpg",
    lamp:        "assets/home.jpg",
    clock:       "assets/home.jpg",
    led:         "assets/home.jpg",
    // Beauty / belleza
    belleza:   "assets/placeholder.png",
    beauty:    "assets/placeholder.png",
    facial:    "assets/placeholder.png",
    skincare:  "assets/placeholder.png",
    makeup:    "assets/placeholder.png",
    slippers:  "assets/placeholder.png",
    // Tech / tecnologia
    tech:       "assets/placeholder.png",
    tecnologia: "assets/placeholder.png",
    earbuds:    "assets/placeholder.png",
    charger:    "assets/placeholder.png",
    keyboard:   "assets/placeholder.png",
    webcam:     "assets/placeholder.png",
    watch:      "assets/placeholder.png",
    // Automotive / automocion
    automotive: "assets/home.jpg",
    automocion: "assets/home.jpg",
    auto:       "assets/home.jpg",
    car:        "assets/home.jpg",
    // Industrial / tools
    tools:      "assets/placeholder.png",
    herramientas: "assets/placeholder.png",
    industrial: "assets/placeholder.png",
    drill:      "assets/placeholder.png",
    // Fitness
    fitness:    "assets/placeholder.png",
    workout:    "assets/placeholder.png",
    yoga:       "assets/placeholder.png",
    // Generic fallback
    "default":  "assets/placeholder.png"
  };

  // ── URL patterns that are known to be unreliable ─────────────────────────
  var BLOCKED_HOSTS = [
    "m.media-amazon.com",
    "images-amazon.com",
    "source.unsplash.com",
    "picsum.photos",
    "via.placeholder.com"
  ];

  // ── SVG inline placeholder (no network request) ───────────────────────────
  var SVG_PLACEHOLDER =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 300 300'%3E" +
    "%3Crect width='300' height='300' fill='%23f1f5f9'/%3E" +
    "%3Cpath d='M150 95c-15 0-27 12-27 27s12 27 27 27 27-12 27-27-12-27-27-27zm-55 110c0-30 25-55 55-55s55 25 55 55H95z' fill='%23cbd5e1'/%3E" +
    "%3C/svg%3E";

  // ── Broken URL log ────────────────────────────────────────────────────────
  var _brokenLog = [];

  function _logBroken(url, category) {
    if (!url || url === SVG_PLACEHOLDER) return;
    _brokenLog.push({ url: url, category: category, ts: new Date().toISOString() });
    console.warn("[LcaImageLoader] Broken image URL →", url, "| category:", category || "unknown");
  }

  // ── Normalize category key ────────────────────────────────────────────────
  function _normalizeKey(str) {
    return String(str || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  // ── Pick fallback for a given category string ─────────────────────────────
  function _fallbackForCategory(category) {
    var key = _normalizeKey(category);
    if (CATEGORY_ASSETS[key]) return CATEGORY_ASSETS[key];
    // Try substring match
    var keys = Object.keys(CATEGORY_ASSETS);
    for (var i = 0; i < keys.length; i++) {
      if (key.includes(keys[i]) || keys[i].includes(key)) {
        return CATEGORY_ASSETS[keys[i]];
      }
    }
    return CATEGORY_ASSETS["default"];
  }

  // ── Check if a URL is in a blocked host ──────────────────────────────────
  function _isBlocked(url) {
    if (!url) return true;
    var lower = url.toLowerCase();
    for (var i = 0; i < BLOCKED_HOSTS.length; i++) {
      if (lower.includes(BLOCKED_HOSTS[i])) return true;
    }
    return false;
  }

  // ── Wrap an <img> with a skeleton div ────────────────────────────────────
  function _wrapWithSkeleton(img) {
    // Don't double-wrap
    if (img.parentElement && img.parentElement.classList.contains("lca-img-wrap")) return;
    var wrapper = document.createElement("div");
    wrapper.className = "lca-img-wrap";
    wrapper.style.cssText = "position:relative;overflow:hidden;background:#f1f5f9;";

    // Copy dimensions from img or its container
    var w = img.getAttribute("width") || "";
    var h = img.getAttribute("height") || "";
    if (h) wrapper.style.height = isNaN(h) ? h : h + "px";

    var skeleton = document.createElement("div");
    skeleton.className = "lca-skeleton";

    img.parentNode.insertBefore(wrapper, img);
    wrapper.appendChild(skeleton);
    wrapper.appendChild(img);
    return wrapper;
  }

  // ── Apply a src to an img, ensuring object-fit ───────────────────────────
  function _applySrc(img, src) {
    img.style.objectFit = img.style.objectFit || "cover";
    img.src = src;
  }

  // ── Attach onerror fallback chain to an img ───────────────────────────────
  function _attachFallback(img) {
    var originalSrc = img.getAttribute("data-src") || img.getAttribute("src") || "";
    var category    = img.getAttribute("data-category") || img.getAttribute("data-cat") || "";
    var explicitFb  = img.getAttribute("data-fallback") || "";
    var fallback    = explicitFb || _fallbackForCategory(category);
    var tried       = false;

    img.addEventListener("load", function () {
      // Remove skeleton shimmer on load
      var skeleton = img.parentElement && img.parentElement.querySelector(".lca-skeleton");
      if (skeleton) skeleton.style.display = "none";
      img.style.opacity = "1";
    });

    img.addEventListener("error", function () {
      var currentSrc = img.src || "";
      _logBroken(currentSrc, category);

      if (!tried && fallback && currentSrc !== fallback) {
        tried = true;
        _applySrc(img, fallback);
      } else if (img.src !== SVG_PLACEHOLDER) {
        _applySrc(img, SVG_PLACEHOLDER);
      }
    });
  }

  // ── Upgrade a single img element ─────────────────────────────────────────
  function _upgradeImg(img) {
    // Already processed
    if (img._lcaUpgraded) return;
    img._lcaUpgraded = true;

    // Enforce object-fit and hide until loaded
    img.style.objectFit = img.style.objectFit || "cover";
    img.style.opacity   = img.complete && img.naturalWidth > 0 ? "1" : "0";
    img.style.transition = "opacity 0.3s ease";

    var category = img.getAttribute("data-category") || img.getAttribute("data-cat") || "";

    // Block known broken CDN hosts immediately
    var dataSrc = img.getAttribute("data-src");
    var src = dataSrc || img.getAttribute("src") || "";

    if (_isBlocked(src)) {
      _logBroken(src, category);
      src = _fallbackForCategory(category);
      dataSrc = null; // skip lazy loading, use fallback directly
    }

    _attachFallback(img);
    _wrapWithSkeleton(img);

    // Lazy load via data-src
    if (dataSrc) {
      img.removeAttribute("src"); // prevent immediate load
      img.setAttribute("data-src", dataSrc);
    } else {
      _applySrc(img, src || SVG_PLACEHOLDER);
    }
  }

  // ── IntersectionObserver lazy loader ─────────────────────────────────────
  var _observer = null;

  function _getObserver() {
    if (_observer) return _observer;
    if (!window.IntersectionObserver) return null;
    _observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var img = entry.target;
        var src = img.getAttribute("data-src");
        if (src) {
          img.removeAttribute("data-src");
          _applySrc(img, src);
        }
        _observer.unobserve(img);
      });
    }, { rootMargin: "200px 0px" });
    return _observer;
  }

  // ── Upgrade all imgs in a container ──────────────────────────────────────
  function upgrade(container) {
    var root = container || document;
    var imgs  = root.querySelectorAll("img.lca-img, img[data-src], .hub-card-img-wrap img, .prod-card-img img, .market-thumb, .cart-item-img");
    var obs   = _getObserver();

    imgs.forEach(function (img) {
      _upgradeImg(img);
      var hasPendingSrc = img.getAttribute("data-src");
      if (hasPendingSrc && obs) {
        obs.observe(img);
      }
    });
  }

  // ── Patch hub card rendering to add data-category ─────────────────────────
  function patchHubImages() {
    // After hub renders, tag images with category based on their section
    document.querySelectorAll(".hub-section").forEach(function (section) {
      var id = section.id || "";
      section.querySelectorAll("img").forEach(function (img) {
        if (!img.getAttribute("data-category")) {
          img.setAttribute("data-category", id.replace("hub-", ""));
        }
        _upgradeImg(img);
      });
    });
  }

  // ── Public API ────────────────────────────────────────────────────────────
  function init() {
    upgrade(document);

    // Re-run after dynamic hub sections render
    var hubContainer = document.getElementById("hub-sections-container");
    if (hubContainer) {
      var mo = new (window.MutationObserver || function () {})(function () {
        patchHubImages();
      });
      if (mo.observe) mo.observe(hubContainer, { childList: true, subtree: false });
    }

    // Also run after any section renders (small delay for deferred renders)
    setTimeout(function () { upgrade(document); patchHubImages(); }, 400);
    setTimeout(function () { upgrade(document); patchHubImages(); }, 1200);
  }

  root.LcaImageLoader = {
    init:              init,
    upgrade:           upgrade,
    fallbackForCategory: _fallbackForCategory,
    isBlocked:         _isBlocked,
    getBrokenLog:      function () { return _brokenLog.slice(); },
    SVG_PLACEHOLDER:   SVG_PLACEHOLDER,
    CATEGORY_ASSETS:   CATEGORY_ASSETS
  };

  // Auto-init on DOMContentLoaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
