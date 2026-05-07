/**
 * AMATOTY – International i18n Module
 * Handles: language detection, geo/IP detection, currency conversion,
 *           translations (EN/ES/PT), locale banner, switcher modal,
 *           localStorage persistence, hreflang injection.
 *
 * Usage: included in <head> before other scripts.
 * Public API: window.I18N
 */
(function () {
  'use strict';

  // ── STORAGE KEYS ────────────────────────────────────────────────────────
  const KEY_LANG     = 'amatoty_lang';
  const KEY_CURRENCY = 'amatoty_currency';
  const KEY_COUNTRY  = 'amatoty_country';
  const KEY_RATES    = 'amatoty_fx_rates';
  const KEY_RATES_TS = 'amatoty_fx_ts';
  const KEY_MANUAL   = 'amatoty_manual'; // "1" if user set manually

  // ── COUNTRY → LANGUAGE ──────────────────────────────────────────────────
  const COUNTRY_LANG = {
    PE:'es', CO:'es', MX:'es', CL:'es', AR:'es', EC:'es',
    BO:'es', PY:'es', UY:'es', VE:'es', CR:'es', PA:'es',
    GT:'es', SV:'es', HN:'es', NI:'es', CU:'es', DO:'es', PR:'es',
    BR:'pt', PT:'pt', AO:'pt', MZ:'pt',
    US:'en', GB:'en', AU:'en', CA:'en', NZ:'en', IE:'en', ZA:'en',
    IN:'en', PH:'en', SG:'en', NG:'en',
  };

  // ── COUNTRY → DEFAULT CURRENCY ──────────────────────────────────────────
  const COUNTRY_CURRENCY = {
    PE:'PEN', CO:'COP', MX:'MXN', CL:'CLP', AR:'ARS', EC:'USD',
    BO:'BOB', PY:'PYG', UY:'UYU', BR:'BRL', VE:'USD',
    US:'USD', GB:'GBP', AU:'AUD', CA:'CAD', NZ:'NZD',
    CR:'CRC', GT:'GTQ', HN:'HNL', IN:'INR', SG:'SGD',
  };

  // ── CURRENCY SYMBOLS ─────────────────────────────────────────────────────
  const CURRENCY_SYMBOLS = {
    USD:'$', PEN:'S/', COP:'$', MXN:'$', CLP:'$', ARS:'$',
    BOB:'Bs', PYG:'₲', UYU:'$', BRL:'R$', GBP:'£', EUR:'€',
    CAD:'CA$', AUD:'A$', NZD:'NZ$', INR:'₹', SGD:'S$',
    CRC:'₡', GTQ:'Q', HNL:'L',
  };

  // ── COUNTRY NAMES ────────────────────────────────────────────────────────
  const COUNTRY_NAMES = {
    PE:'Perú', CO:'Colombia', MX:'México', CL:'Chile', AR:'Argentina',
    EC:'Ecuador', BO:'Bolivia', PY:'Paraguay', UY:'Uruguay', BR:'Brasil',
    VE:'Venezuela', US:'United States', GB:'United Kingdom', AU:'Australia',
    CA:'Canada', NZ:'New Zealand', CR:'Costa Rica', GT:'Guatemala',
    HN:'Honduras', SV:'El Salvador', NI:'Nicaragua', CU:'Cuba',
    DO:'Rep. Dominicana', PR:'Puerto Rico', PT:'Portugal',
  };

  // ── LANGUAGE NAMES ───────────────────────────────────────────────────────
  const LANG_NAMES = { en:'English', es:'Español', pt:'Português' };

  // ── FALLBACK RATES (USD base) ────────────────────────────────────────────
  const FALLBACK_RATES = {
    USD:1, PEN:3.75, COP:4100, MXN:17.2, CLP:950, ARS:1100,
    BOB:6.9, PYG:7400, UYU:40, BRL:5.2, GBP:0.79, EUR:0.92,
    CAD:1.37, AUD:1.53, INR:83, SGD:1.35,
  };

  // ── TRANSLATIONS ─────────────────────────────────────────────────────────
  const STRINGS = {
    en: {
      // Navigation
      nav_home:           'Home',
      nav_smart_search:   'Smart Search',
      nav_categories:     'Categories',
      nav_product_panel:  'Product Panel',
      nav_blog:           'Blog',
      nav_about:          'About us',
      nav_contact:        'Contact',
      // Location bar
      market:             'Market',
      currency_label:     'Currency',
      loading_catalog:    'Loading catalog...',
      // Category strip
      cat_all:            'All',
      view_all:           'View all',
      // Sidebar
      filter_results:     'Filter results',
      delivery_type:      'Delivery type',
      opt_all:            'All',
      opt_in_stock:       'In stock',
      opt_quote:          'Request quote',
      brand:              'Brand',
      quality:            'Quality',
      opt_professional:   'Professional',
      opt_premium:        'Premium',
      opt_economy:        'Economy',
      min_price:          'Minimum price',
      max_price:          'Maximum price',
      compatibility:      'Compatibility / size',
      compat_ph:          'model, size, standard',
      material:           'Material',
      material_ph:        'steel, rubber, plastic',
      image_audio:        '📷 Image or audio (AI)',
      upload_hint:        'Upload product photo or voice note',
      btn_search:         '🔍 Search',
      btn_clear:          'Clear filters',
      btn_record:         '🎤 Record audio',
      // Results
      results:            'Results',
      sort_by:            'Sort by:',
      sort_recommended:   'Recommended',
      sort_price_asc:     'Lowest price',
      sort_price_desc:    'Highest price',
      sort_category:      'Category',
      // Cart
      my_cart:            '🛒 My Cart',
      subtotal:           'Subtotal',
      total:              'Total',
      btn_checkout:       'Place order',
      btn_empty_cart:     'Empty cart',
      add_to_cart:        'Add to cart',
      see_offer:          'See offer',
      in_stock:           'In stock',
      quote_only:         'Quote only',
      // Product detail
      product_info:       'Product details',
      spec_brand:         'Brand',
      spec_model:         'Model',
      spec_quality:       'Quality',
      spec_stock:         'Stock',
      spec_warranty:      'Warranty',
      spec_rating:        'Rating',
      spec_sector:        'Sector',
      spec_material:      'Material',
      spec_compat:        'Compatibility',
      available_at:       'Available at',
      // Placeholders
      search_ph:          'What product are you looking for?',
      all_categories:     'All categories',
      location_title:     'My location',
      cart_title:         'Cart',
      no_limit:           'No limit',
      // Locale banner & modal
      locale_banner:      'Viewing prices in {sym} {cur} · Site language: {lang}',
      btn_change_locale:  'Change',
      modal_title:        'Language & Currency',
      modal_lang_label:   'Language',
      modal_country_label:'Country / Market',
      modal_currency_label:'Currency',
      modal_save:         'Save preferences',
      modal_close:        '✕',
      rate_updated:       'Rates updated',
      rate_source:        'Source: open.er-api.com',
      price_original:     'Original price',
      // Page titles
      page_title_smart:   'Smart Search – AMATOTY',
      page_title_home:    'AMATOTY – International Marketplace',
      page_title_oye:     'Oye Bonita – Facial Diagnosis',
      page_title_cat:     'Categories – AMATOTY',
    },
    es: {
      nav_home:           'Inicio',
      nav_smart_search:   'Busca Inteligente',
      nav_categories:     'Categorías',
      nav_product_panel:  'Panel Productos',
      nav_blog:           'Blog',
      nav_about:          'Sobre nosotros',
      nav_contact:        'Contacto',
      market:             'Mercado',
      currency_label:     'Moneda',
      loading_catalog:    'Cargando catálogo...',
      cat_all:            'Ver todo',
      view_all:           'Ver todo',
      filter_results:     'Filtrar resultados',
      delivery_type:      'Tipo de entrega',
      opt_all:            'Todas',
      opt_in_stock:       'Con stock',
      opt_quote:          'A cotizar',
      brand:              'Marca',
      quality:            'Calidad',
      opt_professional:   'Profesional',
      opt_premium:        'Premium',
      opt_economy:        'Económica',
      min_price:          'Precio mínimo',
      max_price:          'Precio máximo',
      compatibility:      'Compatibilidad / medida',
      compat_ph:          'modelo, medida, norma',
      material:           'Material',
      material_ph:        'acero, caucho, plástico',
      image_audio:        '📷 Imagen o audio (IA)',
      upload_hint:        'Sube foto del producto o nota de voz',
      btn_search:         '🔍 Buscar',
      btn_clear:          'Limpiar filtros',
      btn_record:         '🎤 Grabar audio',
      results:            'Resultados',
      sort_by:            'Ordenar por:',
      sort_recommended:   'Recomendados',
      sort_price_asc:     'Menor precio',
      sort_price_desc:    'Mayor precio',
      sort_category:      'Categoría',
      my_cart:            '🛒 Mi Carrito',
      subtotal:           'Subtotal',
      total:              'Total',
      btn_checkout:       'Generar pedido',
      btn_empty_cart:     'Vaciar carrito',
      add_to_cart:        'Agregar al carrito',
      see_offer:          'Ver oferta',
      in_stock:           'Con stock',
      quote_only:         'A cotizar',
      product_info:       'Ficha de producto',
      spec_brand:         'Marca',
      spec_model:         'Modelo',
      spec_quality:       'Calidad',
      spec_stock:         'Stock',
      spec_warranty:      'Garantía',
      spec_rating:        'Calificación',
      spec_sector:        'Sector',
      spec_material:      'Material',
      spec_compat:        'Compatibilidad',
      available_at:       'Disponible en',
      search_ph:          '¿Qué producto buscas?',
      all_categories:     'Todas las categorías',
      location_title:     'Mi ubicación',
      cart_title:         'Carrito',
      no_limit:           'Sin límite',
      locale_banner:      'Viendo precios en {sym} {cur} · Idioma del sitio: {lang}',
      btn_change_locale:  'Cambiar',
      modal_title:        'Idioma y moneda',
      modal_lang_label:   'Idioma',
      modal_country_label:'País / Mercado',
      modal_currency_label:'Moneda',
      modal_save:         'Guardar preferencias',
      modal_close:        '✕',
      rate_updated:       'Tipo de cambio actualizado',
      rate_source:        'Fuente: open.er-api.com',
      price_original:     'Precio original',
      page_title_smart:   'Busca Inteligente – AMATOTY',
      page_title_home:    'AMATOTY – Marketplace Internacional',
      page_title_oye:     'Oye Bonita – Diagnóstico Facial',
      page_title_cat:     'Categorías – AMATOTY',
    },
    pt: {
      nav_home:           'Início',
      nav_smart_search:   'Busca Inteligente',
      nav_categories:     'Categorias',
      nav_product_panel:  'Painel Produtos',
      nav_blog:           'Blog',
      nav_about:          'Sobre nós',
      nav_contact:        'Contato',
      market:             'Mercado',
      currency_label:     'Moeda',
      loading_catalog:    'Carregando catálogo...',
      cat_all:            'Ver tudo',
      view_all:           'Ver tudo',
      filter_results:     'Filtrar resultados',
      delivery_type:      'Tipo de entrega',
      opt_all:            'Todas',
      opt_in_stock:       'Em estoque',
      opt_quote:          'Sob cotação',
      brand:              'Marca',
      quality:            'Qualidade',
      opt_professional:   'Profissional',
      opt_premium:        'Premium',
      opt_economy:        'Econômica',
      min_price:          'Preço mínimo',
      max_price:          'Preço máximo',
      compatibility:      'Compatibilidade / medida',
      compat_ph:          'modelo, medida, norma',
      material:           'Material',
      material_ph:        'aço, borracha, plástico',
      image_audio:        '📷 Imagem ou áudio (IA)',
      upload_hint:        'Envie foto do produto ou nota de voz',
      btn_search:         '🔍 Buscar',
      btn_clear:          'Limpar filtros',
      btn_record:         '🎤 Gravar áudio',
      results:            'Resultados',
      sort_by:            'Ordenar por:',
      sort_recommended:   'Recomendados',
      sort_price_asc:     'Menor preço',
      sort_price_desc:    'Maior preço',
      sort_category:      'Categoria',
      my_cart:            '🛒 Meu Carrinho',
      subtotal:           'Subtotal',
      total:              'Total',
      btn_checkout:       'Gerar pedido',
      btn_empty_cart:     'Esvaziar carrinho',
      add_to_cart:        'Adicionar ao carrinho',
      see_offer:          'Ver oferta',
      in_stock:           'Em estoque',
      quote_only:         'Sob cotação',
      product_info:       'Ficha do produto',
      spec_brand:         'Marca',
      spec_model:         'Modelo',
      spec_quality:       'Qualidade',
      spec_stock:         'Estoque',
      spec_warranty:      'Garantia',
      spec_rating:        'Avaliação',
      spec_sector:        'Setor',
      spec_material:      'Material',
      spec_compat:        'Compatibilidade',
      available_at:       'Disponível em',
      search_ph:          'Qual produto você procura?',
      all_categories:     'Todas as categorias',
      location_title:     'Minha localização',
      cart_title:         'Carrinho',
      no_limit:           'Sem limite',
      locale_banner:      'Vendo preços em {sym} {cur} · Idioma do site: {lang}',
      btn_change_locale:  'Alterar',
      modal_title:        'Idioma e moeda',
      modal_lang_label:   'Idioma',
      modal_country_label:'País / Mercado',
      modal_currency_label:'Moeda',
      modal_save:         'Salvar preferências',
      modal_close:        '✕',
      rate_updated:       'Taxa de câmbio atualizada',
      rate_source:        'Fonte: open.er-api.com',
      price_original:     'Preço original',
      page_title_smart:   'Busca Inteligente – AMATOTY',
      page_title_home:    'AMATOTY – Marketplace Internacional',
      page_title_oye:     'Oye Bonita – Diagnóstico Facial',
      page_title_cat:     'Categorias – AMATOTY',
    },
  };

  // ── STATE ────────────────────────────────────────────────────────────────
  let _lang     = 'en';
  let _country  = 'US';
  let _currency = 'USD';
  let _rates    = Object.assign({}, FALLBACK_RATES);
  let _ratesDate = '';
  let _initialized = false;

  // ── HELPERS ──────────────────────────────────────────────────────────────
  function safeLS(key, val) {
    try {
      if (val !== undefined) localStorage.setItem(key, val);
      else return localStorage.getItem(key);
    } catch (e) { return null; }
  }

  function detectBrowserLang() {
    const nav = (navigator.language || navigator.userLanguage || 'en').split('-')[0].toLowerCase();
    if (nav === 'es') return 'es';
    if (nav === 'pt') return 'pt';
    return 'en';
  }

  function langToLocale(lang) {
    return { en:'en-US', es:'es-419', pt:'pt-BR' }[lang] || 'en-US';
  }

  // ── EXCHANGE RATES ───────────────────────────────────────────────────────
  async function loadRates() {
    const cached   = safeLS(KEY_RATES);
    const cachedTs = safeLS(KEY_RATES_TS);
    if (cached && cachedTs && (Date.now() - parseInt(cachedTs, 10)) < 86_400_000) {
      try {
        _rates     = JSON.parse(cached);
        _ratesDate = new Date(parseInt(cachedTs, 10)).toLocaleDateString();
        return;
      } catch (e) { /* fall through */ }
    }
    try {
      const res  = await fetch('https://open.er-api.com/v6/latest/USD', { cache:'no-store' });
      const data = await res.json();
      if (data && data.rates) {
        _rates = data.rates;
        safeLS(KEY_RATES,    JSON.stringify(_rates));
        safeLS(KEY_RATES_TS, String(Date.now()));
        _ratesDate = new Date().toLocaleDateString();
      }
    } catch (e) {
      _rates = Object.assign({}, FALLBACK_RATES);
    }
  }

  // ── GEO DETECTION ────────────────────────────────────────────────────────
  async function detectGeo() {
    // Always restore manual preferences first
    const isManual = safeLS(KEY_MANUAL) === '1';
    if (isManual) {
      _lang     = safeLS(KEY_LANG)     || detectBrowserLang();
      _country  = safeLS(KEY_COUNTRY)  || 'US';
      _currency = safeLS(KEY_CURRENCY) || COUNTRY_CURRENCY[_country] || 'USD';
      return;
    }

    // Try IP geolocation (free, 1k/day, HTTPS only)
    let detected = false;
    if (window.location.protocol === 'https:' || window.location.hostname === '127.0.0.1') {
      try {
        const res  = await fetch('https://ipapi.co/json/', { cache:'no-store' });
        const data = await res.json();
        if (data && data.country_code && !data.error) {
          _country  = data.country_code;
          _currency = COUNTRY_CURRENCY[_country] || 'USD';
          _lang     = COUNTRY_LANG[_country]     || detectBrowserLang();
          detected  = true;
        }
      } catch (e) { /* ignore */ }
    }

    if (!detected) {
      _lang     = detectBrowserLang();
      _country  = 'US';
      _currency = 'USD';
    }

    // Browser language overrides IP language if it's not English
    const bl = detectBrowserLang();
    if (bl !== 'en') _lang = bl;

    // Restore any previously stored soft preferences
    if (safeLS(KEY_LANG))     _lang     = safeLS(KEY_LANG);
    if (safeLS(KEY_CURRENCY)) _currency = safeLS(KEY_CURRENCY);
    if (safeLS(KEY_COUNTRY))  _country  = safeLS(KEY_COUNTRY);
  }

  // ── CURRENCY CONVERSION ──────────────────────────────────────────────────
  function convertPrice(amountUSD, targetCurrency) {
    const rate = _rates[targetCurrency || _currency] || 1;
    return Number(amountUSD || 0) * rate;
  }

  function formatPrice(amountUSD, currency) {
    currency = currency || _currency;
    const converted = convertPrice(amountUSD, currency);
    try {
      return new Intl.NumberFormat(langToLocale(_lang), {
        style:'currency', currency, maximumFractionDigits:2,
      }).format(converted);
    } catch (e) {
      const sym = CURRENCY_SYMBOLS[currency] || currency;
      return `${sym} ${converted.toFixed(2)}`;
    }
  }

  // ── TRANSLATE ────────────────────────────────────────────────────────────
  function t(key, vars) {
    const dict = STRINGS[_lang] || STRINGS.en;
    let str = dict[key] !== undefined ? dict[key] : (STRINGS.en[key] !== undefined ? STRINGS.en[key] : key);
    if (vars) {
      Object.keys(vars).forEach(k => {
        str = str.replace(new RegExp('\\{' + k + '\\}', 'g'), vars[k]);
      });
    }
    return str;
  }

  function applyTranslations() {
    document.documentElement.lang = _lang;

    // data-i18n="key"                 → textContent
    // data-i18n="key" data-i18n-attr  → setAttribute(attr, val)
    // data-i18n-ph="key"              → placeholder
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key  = el.getAttribute('data-i18n');
      const attr = el.getAttribute('data-i18n-attr');
      const val  = t(key);
      if (attr) { el.setAttribute(attr, val); }
      else      { el.textContent = val; }
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
      el.placeholder = t(el.getAttribute('data-i18n-ph'));
    });

    // Page title
    const titleKey = document.body.dataset.pageTitle;
    if (titleKey) document.title = t(titleKey);

    // Sync page country/currency dropdowns if present
    syncSelectors();
  }

  function syncSelectors() {
    const countryEl  = document.getElementById('country');
    const currencyEl = document.getElementById('currency');
    if (countryEl  && countryEl.querySelector(`option[value="${_country}"]`))   countryEl.value  = _country;
    if (currencyEl && currencyEl.querySelector(`option[value="${_currency}"]`)) currencyEl.value = _currency;
  }

  // ── LOCALE BANNER ────────────────────────────────────────────────────────
  function renderBanner() {
    let banner = document.getElementById('i18n-locale-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'i18n-locale-banner';
      Object.assign(banner.style, {
        position:'fixed', bottom:'0', left:'0', right:'0', zIndex:'10000',
        background:'#1e3a5f', color:'#fff', fontSize:'13px', fontWeight:'600',
        display:'flex', alignItems:'center', justifyContent:'center', gap:'10px',
        padding:'7px 16px', boxShadow:'0 -2px 12px rgba(0,0,0,.2)',
        fontFamily:'Arial,sans-serif', lineHeight:'1.4',
      });
      document.body.appendChild(banner);
    }
    const sym      = CURRENCY_SYMBOLS[_currency] || _currency;
    const langName = LANG_NAMES[_lang] || _lang.toUpperCase();
    banner.innerHTML = `
      <span>📍 ${t('locale_banner', {sym, cur:_currency, lang:langName})}</span>
      <button
        onclick="window.I18N.openModal()"
        style="background:#ff9900;color:#fff;border:none;border-radius:6px;
               padding:4px 12px;font-weight:700;font-size:12px;cursor:pointer"
      >${t('btn_change_locale')}</button>
      <button
        onclick="this.parentElement.style.display='none'"
        aria-label="Close"
        style="background:none;border:none;color:#94a3b8;font-size:18px;
               cursor:pointer;line-height:1;padding:0 4px"
      >✕</button>
    `;
  }

  // ── MODAL ────────────────────────────────────────────────────────────────
  function buildCountryOptions() {
    return Object.entries(COUNTRY_NAMES).map(([cc, name]) => {
      const sel = cc === _country ? 'selected' : '';
      return `<option value="${cc}" ${sel}>${name}</option>`;
    }).join('');
  }

  function buildCurrencyOptions() {
    return Object.keys(CURRENCY_SYMBOLS).map(c => {
      const sel = c === _currency ? 'selected' : '';
      return `<option value="${c}" ${sel}>${c} ${CURRENCY_SYMBOLS[c]}</option>`;
    }).join('');
  }

  function buildLangOptions() {
    return Object.entries(LANG_NAMES).map(([l, name]) => {
      const sel = l === _lang ? 'selected' : '';
      return `<option value="${l}" ${sel}>${name}</option>`;
    }).join('');
  }

  function openModal() {
    let modal = document.getElementById('i18n-modal');
    if (modal) { modal.remove(); }

    modal = document.createElement('div');
    modal.id = 'i18n-modal';
    Object.assign(modal.style, {
      position:'fixed', inset:'0', background:'rgba(0,0,0,.55)',
      zIndex:'20000', display:'flex', alignItems:'center',
      justifyContent:'center', padding:'20px', fontFamily:'Arial,sans-serif',
    });

    modal.innerHTML = `
      <div style="background:#fff;border-radius:14px;max-width:420px;width:100%;
                  padding:28px;box-shadow:0 20px 60px rgba(0,0,0,.3);position:relative">
        <button onclick="window.I18N.closeModal()"
          style="position:absolute;top:12px;right:14px;background:none;border:none;
                 font-size:22px;cursor:pointer;color:#6b7280;line-height:1">
          ${t('modal_close')}
        </button>
        <h2 style="margin:0 0 20px;font-size:18px;color:#1e3a5f;font-weight:900">
          🌍 ${t('modal_title')}
        </h2>

        <label style="display:block;font-size:11px;font-weight:800;color:#6b7280;
                      text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">
          ${t('modal_lang_label')}
        </label>
        <select id="i18n-sel-lang"
          style="width:100%;border:1px solid #d1d5db;border-radius:8px;
                 padding:9px 12px;font-size:14px;margin-bottom:14px">
          ${buildLangOptions()}
        </select>

        <label style="display:block;font-size:11px;font-weight:800;color:#6b7280;
                      text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">
          ${t('modal_country_label')}
        </label>
        <select id="i18n-sel-country"
          style="width:100%;border:1px solid #d1d5db;border-radius:8px;
                 padding:9px 12px;font-size:14px;margin-bottom:14px">
          ${buildCountryOptions()}
        </select>

        <label style="display:block;font-size:11px;font-weight:800;color:#6b7280;
                      text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">
          ${t('modal_currency_label')}
        </label>
        <select id="i18n-sel-currency"
          style="width:100%;border:1px solid #d1d5db;border-radius:8px;
                 padding:9px 12px;font-size:14px;margin-bottom:8px">
          ${buildCurrencyOptions()}
        </select>

        ${_ratesDate
          ? `<p style="font-size:11px;color:#9ca3af;margin:0 0 16px">
               🔄 ${t('rate_updated')}: ${_ratesDate} — ${t('rate_source')}
             </p>`
          : '<div style="margin-bottom:16px"></div>'}

        <button onclick="window.I18N.saveModal()"
          style="width:100%;background:linear-gradient(135deg,#ff9900,#d97706);
                 color:#fff;border:none;border-radius:8px;padding:13px;
                 font-weight:900;font-size:15px;cursor:pointer">
          ${t('modal_save')}
        </button>
      </div>
    `;

    modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
    document.body.appendChild(modal);
  }

  function closeModal() {
    const m = document.getElementById('i18n-modal');
    if (m) m.remove();
  }

  function saveModal() {
    const lang     = document.getElementById('i18n-sel-lang').value;
    const country  = document.getElementById('i18n-sel-country').value;
    const currency = document.getElementById('i18n-sel-currency').value;
    setLocale(lang, country, currency, true);
    closeModal();
  }

  // ── SET LOCALE ───────────────────────────────────────────────────────────
  function setLocale(lang, country, currency, manual) {
    _lang     = lang     || _lang;
    _country  = country  || _country;
    _currency = currency || _currency;

    safeLS(KEY_LANG,     _lang);
    safeLS(KEY_COUNTRY,  _country);
    safeLS(KEY_CURRENCY, _currency);
    if (manual) safeLS(KEY_MANUAL, '1');

    applyTranslations();
    renderBanner();

    // Dispatch event for other scripts (smart-search fx, cart, etc.)
    window.dispatchEvent(new CustomEvent('i18n:change', {
      detail: { lang: _lang, country: _country, currency: _currency },
    }));
  }

  // ── HREFLANG INJECTION ───────────────────────────────────────────────────
  function injectHreflang() {
    if (document.querySelector('link[hreflang]')) return; // already set
    const baseUrl = window.location.origin + window.location.pathname
      .replace(/\/(en|es|pt)\//i, '/');

    [
      { hreflang:'en',        href: baseUrl },
      { hreflang:'es',        href: baseUrl },
      { hreflang:'pt',        href: baseUrl },
      { hreflang:'x-default', href: baseUrl },
    ].forEach(({ hreflang, href }) => {
      const link = Object.assign(document.createElement('link'), {
        rel:'alternate', hreflang, href,
      });
      document.head.appendChild(link);
    });
  }

  // ── INIT ─────────────────────────────────────────────────────────────────
  async function init() {
    if (_initialized) return;
    _initialized = true;
    await Promise.all([detectGeo(), loadRates()]);
    applyTranslations();
    renderBanner();
    injectHreflang();
  }

  // ── PUBLIC API ───────────────────────────────────────────────────────────
  window.I18N = {
    t,
    init,
    openModal,
    closeModal,
    saveModal,
    setLocale,
    formatPrice,
    convertPrice,
    applyTranslations,
    getLang:     () => _lang,
    getCountry:  () => _country,
    getCurrency: () => _currency,
    getRates:    () => _rates,
    getRatesDate:() => _ratesDate,
    getSymbol:   (cur) => CURRENCY_SYMBOLS[cur || _currency] || (cur || _currency),
    COUNTRY_CURRENCY,
    COUNTRY_LANG,
    CURRENCY_SYMBOLS,
    LANG_NAMES,
    STRINGS,
  };

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 0);
  }

})();
