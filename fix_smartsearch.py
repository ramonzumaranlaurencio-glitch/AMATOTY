"""
Patch renderGrid() in docs/smart-search.html to use i18n strings.
"""
import re

FILE = "docs/smart-search.html"

with open(FILE, encoding="utf-8") as f:
    content = f.read()

# ── 1. empty-state ──────────────────────────────────────────────────────────
OLD_EMPTY = (
    'grid.innerHTML=`<div class="empty-state" style="grid-column:1/-1">'
    '<h3>Sin resultados</h3>'
    '<p style="color:var(--ink2)">Prueba con otra búsqueda o limpia los filtros.</p>'
    '</div>`;'
)
NEW_EMPTY = (
    "grid.innerHTML=`<div class=\"empty-state\" style=\"grid-column:1/-1\">"
    "<h3>${esc(_t('no_results'))}</h3>"
    "<p style=\"color:var(--ink2)\">${esc(_t('no_results_hint'))}</p>"
    "</div>`;"
)
assert OLD_EMPTY in content, "OLD_EMPTY not found"
content = content.replace(OLD_EMPTY, NEW_EMPTY, 1)

# ── 2. badge NUEVO ───────────────────────────────────────────────────────────
OLD_BADGE = (
    'isNew?`<span class="prod-badge new">NUEVO</span>`'
)
NEW_BADGE = (
    "isNew?`<span class=\"prod-badge new\">${esc(_t('new_badge'))}</span>`"
)
assert OLD_BADGE in content, "OLD_BADGE not found"
content = content.replace(OLD_BADGE, NEW_BADGE, 1)

# ── 3. shipText ──────────────────────────────────────────────────────────────
OLD_SHIP = (
    'const shipText=Number(p.stock||0)>0?"✓ Disponible":"📋 A cotizar";'
)
NEW_SHIP = (
    "const shipText=Number(p.stock||0)>0?_t('available'):`📋 ${_t('quote_only')}`;",
)
NEW_SHIP = (
    "const shipText=Number(p.stock||0)>0?_t('available'):`\U0001f4cb ${_t('quote_only')}`;"
)
assert OLD_SHIP in content, "OLD_SHIP not found"
content = content.replace(OLD_SHIP, NEW_SHIP, 1)

# ── 4. "Ver oferta en X" ─────────────────────────────────────────────────────
OLD_SEE = (
    'const providerLinks=(p.source_links||[]).slice(0,1).map(l=>'
    '`<a class="btn-see-offer" href="${esc(l.url)}" target="_blank" rel="nofollow noopener">'
    'Ver oferta en ${esc(l.name)}</a>`).join("")'
    '||`<a class="btn-see-offer" href="https://www.amazon.com/s?k=${encodeURIComponent(p.name)}" '
    'target="_blank" rel="nofollow noopener">Ver oferta</a>`;'
)
NEW_SEE = (
    "const seeLabel=_t('see_offer');\n"
    "    const providerLinks=(p.source_links||[]).slice(0,1).map(l=>"
    "`<a class=\"btn-see-offer\" href=\"${esc(l.url)}\" target=\"_blank\" rel=\"nofollow noopener\">"
    "${esc(seeLabel)} ${esc(l.name)}</a>`).join(\"\")"
    "||`<a class=\"btn-see-offer\" href=\"https://www.amazon.com/s?k=${encodeURIComponent(p.name)}&tag=amatotyshop-20\" "
    "target=\"_blank\" rel=\"nofollow noopener\">${esc(seeLabel)}</a>`;"
)
assert OLD_SEE in content, "OLD_SEE not found"
content = content.replace(OLD_SEE, NEW_SEE, 1)

# ── 5. title="Guardar" → use _t ──────────────────────────────────────────────
OLD_FAV = 'title="Guardar" onclick="event.stopPropagation()">♡</button>'
NEW_FAV = "title=\"Save\" onclick=\"event.stopPropagation()\">♡</button>"
assert OLD_FAV in content, "OLD_FAV not found"
content = content.replace(OLD_FAV, NEW_FAV, 1)

# ── 6. "🛒 Agregar al carrito" → use _t ──────────────────────────────────────
OLD_CART = '🛒 Agregar al carrito</button>'
NEW_CART = "🛒 ${esc(_t('add_to_cart'))}</button>"
assert OLD_CART in content, "OLD_CART not found"
content = content.replace(OLD_CART, NEW_CART, 1)

# ── 7. "💡 Mejor precio:" → use _t ───────────────────────────────────────────
OLD_BEST = "adv.innerHTML=`💡 Mejor precio: <strong>${esc(cheapest.name)}</strong> – ${money(basePrice(cheapest))}`"
NEW_BEST = "adv.innerHTML=`${esc(_t('best_price'))} <strong>${esc(cheapest.name)}</strong> – ${money(basePrice(cheapest))}`"
assert OLD_BEST in content, "OLD_BEST not found"
content = content.replace(OLD_BEST, NEW_BEST, 1)

# ── 8. Add _t helper before buildCatStrip ────────────────────────────────────
# Check if _t() is already defined (from a previous partial run)
if "function _t(key" not in content:
    OLD_CAT = "function buildCatStrip(){"
    NEW_CAT = (
        "function _t(key,vars){"
        "return (window.I18N&&window.I18N.t)?window.I18N.t(key,vars):key;}\n"
        "function buildCatStrip(){"
    )
    assert OLD_CAT in content, "OLD_CAT not found"
    content = content.replace(OLD_CAT, NEW_CAT, 1)

# ── 9. buildCatStrip – fix hardcoded "Todas las categorías" + "Todas" ────────
OLD_CATS_SEL = (
    'sel.innerHTML=`<option value="">Todas las categorías</option>`'
    '+cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join("");'
)
NEW_CATS_SEL = (
    "sel.innerHTML=`<option value=\"\">${esc(_t('all_categories'))}</option>`"
    "+cats.map(c=>`<option value=\"${esc(c)}\">${esc(c)}</option>`).join(\"\");"
)
if OLD_CATS_SEL in content:
    content = content.replace(OLD_CATS_SEL, NEW_CATS_SEL, 1)

OLD_BRAND_SEL = (
    'document.getElementById("brandFilter").innerHTML='
    '`<option value="">Todas</option>`'
    '+brands.map(b=>`<option value="${esc(b)}">${esc(b)}</option>`).join("");'
)
NEW_BRAND_SEL = (
    'document.getElementById("brandFilter").innerHTML='
    "`<option value=\"\">${esc(_t('opt_all'))}</option>`"
    '+brands.map(b=>`<option value="${esc(b)}">${esc(b)}</option>`).join("");'
)
if OLD_BRAND_SEL in content:
    content = content.replace(OLD_BRAND_SEL, NEW_BRAND_SEL, 1)

# ── 10. Add getProductFieldForLang + localized normalize() ───────────────────
if "getProductFieldForLang" not in content:
    OLD_NORMALIZE = (
        'function normalize(p){\n'
        '  const flat = ProductAIGuard.flattenProduct(p);\n'
        '  return Object.assign(flat,{\n'
        '    name: flat.name||flat.nombre||flat.title||flat.titulo||"Producto",'
    )
    NEW_NORMALIZE = (
        '// Returns the best name for a product in the active language\n'
        'function getProductFieldForLang(flat,fallback){\n'
        '  if(typeof flat!=="string"){\n'
        '    const lang=(window.I18N&&window.I18N.getLang)?window.I18N.getLang():"en";\n'
        '    return flat["name_"+lang]||flat["title_"+lang]||fallback||"";\n'
        '  }\n'
        '  return flat||fallback||"";\n'
        '}\n'
        'function normalize(p){\n'
        '  const flat = ProductAIGuard.flattenProduct(p);\n'
        '  const rawName = flat.name||flat.nombre||flat.title||flat.titulo||"Product";\n'
        '  const localName = getProductFieldForLang(flat, rawName);\n'
        '  return Object.assign(flat,{\n'
        '    name: localName,'
    )
    assert OLD_NORMALIZE in content, "OLD_NORMALIZE not found"
    content = content.replace(OLD_NORMALIZE, NEW_NORMALIZE, 1)

# ── 11. Re-render after i18n:change (also rebuild cat strip) ─────────────────
OLD_I18N_CHANGE = (
    "window.addEventListener('i18n:change', function(e) {\n"
    "  const { country, currency } = e.detail;\n"
    "  const countryEl  = document.getElementById('country');\n"
    "  const currencyEl = document.getElementById('currency');\n"
    "  if (countryEl  && countryEl.querySelector(`option[value=\"${country}\"]`))   { countryEl.value  = country;  }\n"
    "  if (currencyEl && currencyEl.querySelector(`option[value=\"${currency}\"]`)) { currencyEl.value = currency; }\n"
    "  if (typeof renderResults === 'function') renderResults();\n"
    "});"
)
NEW_I18N_CHANGE = (
    "window.addEventListener('i18n:change', function(e) {\n"
    "  const { country, currency } = e.detail;\n"
    "  const countryEl  = document.getElementById('country');\n"
    "  const currencyEl = document.getElementById('currency');\n"
    "  if (countryEl  && countryEl.querySelector(`option[value=\"${country}\"]`))   { countryEl.value  = country;  }\n"
    "  if (currencyEl && currencyEl.querySelector(`option[value=\"${currency}\"]`)) { currencyEl.value = currency; }\n"
    "  // Rebuild category strip with new language labels\n"
    "  if (typeof buildCatStrip === 'function' && products.length) buildCatStrip();\n"
    "  if (typeof renderResults === 'function') renderResults();\n"
    "  // Re-render Amazon section if visible\n"
    "  const amzSec = document.getElementById('amazonSection');\n"
    "  const amzPill = document.getElementById('amzQueryPill');\n"
    "  if (amzSec && amzSec.style.display !== 'none' && amzPill && amzPill.textContent) {\n"
    "    if (typeof renderAmazonSection === 'function') renderAmazonSection(amzPill.textContent);\n"
    "  }\n"
    "});"
)
if OLD_I18N_CHANGE in content:
    content = content.replace(OLD_I18N_CHANGE, NEW_I18N_CHANGE, 1)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ smart-search.html patched successfully")
