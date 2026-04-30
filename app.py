
import csv
import json
import re
import uuid
import sqlite3
import textwrap
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime, timedelta, date
from html import escape

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


APP_NAME = "LCA PRO FINAL ÚNICA"
DATA = Path("data")
EXPORTS = Path("exports")
PUBLIC = Path("public_site")
BLOG = PUBLIC / "blog"
CATEGORY = PUBLIC / "category"
ASSETS = PUBLIC / "assets"
VIDEOS = PUBLIC / "videos"
FRAMES = Path("frames")

for d in [DATA, EXPORTS, PUBLIC, BLOG, CATEGORY, ASSETS, VIDEOS, FRAMES]:
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA / "lca_pro_final.db"
CONFIG_PATH = DATA / "config.json"
PRODUCTS_PATH = DATA / "products.json"
ACCOUNTS_PATH = DATA / "accounts.json"

DEFAULT_SLOTS = [9, 12, 15, 18, 21]
VIRAL_HOOKS = [
    "I tested this Amazon product so you don't have to...",
    "This might fix a problem you deal with every day...",
    "Before you buy this, watch this quick review...",
    "I did not expect this to be useful...",
    "Old way vs new way...",
    "Nobody talks about this simple problem...",
    "Stop wasting time with this problem...",
    "This small product is actually practical...",
    "This Amazon find actually makes sense...",
    "I compared this with the normal way..."
]


def inject_css():
    st.markdown("""
<style>
.block-container {padding-top:1rem; padding-left:1.4rem; padding-right:1.4rem; max-width:100%;}
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:#e5e7eb;}
.pro-header {background:linear-gradient(135deg,#0f172a 0%,#164e63 60%,#0a6ed1 100%);padding:24px 28px;border-radius:0 0 24px 24px;color:white;margin-bottom:20px;box-shadow:0 16px 40px rgba(15,23,42,.22);}
.pro-title {font-size:34px;font-weight:900;margin:0;}
.pro-sub {color:#cbd5e1;margin-top:6px;font-size:14px;}
.kpi-card {background:#fff;border:1px solid #dbe3ef;border-radius:18px;padding:18px;box-shadow:0 10px 28px rgba(15,23,42,.06);min-height:112px;}
.kpi-label {color:#64748b;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;}
.kpi-value {color:#0f172a;font-size:30px;font-weight:900;margin-top:8px;}
.kpi-note {color:#64748b;font-size:13px;margin-top:4px;}
.section-card {background:white;border:1px solid #dbe3ef;border-radius:20px;padding:22px;margin:16px 0;box-shadow:0 10px 28px rgba(15,23,42,.05);}
.action-bar {background:#f8fafc;border:1px solid #dbe3ef;padding:16px;border-radius:18px;margin:12px 0 20px;}
.product-card {background:linear-gradient(180deg,#ffffff,#f8fafc);border:1px solid #dbe3ef;border-radius:20px;padding:20px;margin:12px 0;box-shadow:0 10px 26px rgba(15,23,42,.05);}
.status-pill {display:inline-block;padding:5px 11px;border-radius:999px;font-size:12px;font-weight:900;}
.pill-green{background:#dcfce7;color:#166534}.pill-yellow{background:#fef3c7;color:#92400e}.pill-red{background:#fee2e2;color:#991b1b}.pill-blue{background:#dbeafe;color:#1e40af}.pill-gray{background:#f1f5f9;color:#334155}
.alert-good{background:#ecfdf5;border:1px solid #bbf7d0;color:#166534;padding:14px;border-radius:14px}
.alert-warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;padding:14px;border-radius:14px}
.stButton>button{border-radius:12px;font-weight:800;min-height:42px;}
</style>
""", unsafe_allow_html=True)


def header(title, subtitle="Sistema PRO único"):
    st.markdown(f"""
<div class="pro-header">
  <div class="pro-title">{title}</div>
  <div class="pro-sub">{subtitle} · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
</div>
""", unsafe_allow_html=True)


def kpi(label, value, note=""):
    st.markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-note">{note}</div>
</div>
""", unsafe_allow_html=True)


def pill(text):
    t = str(text or "").upper()
    if "SCALE" in t or "POSTED" in t or "ACTIVE" in t or "OK" in t or "READY" in t:
        cls = "pill-green"
    elif "FIX" in t or "TESTING" in t or "PENDING" in t:
        cls = "pill-yellow"
    elif "NEW" in t or "ERROR" in t or "BLOCK" in t:
        cls = "pill-red"
    elif "KEEP" in t:
        cls = "pill-blue"
    else:
        cls = "pill-gray"
    return f'<span class="status-pill {cls}">{escape(str(text or "-"))}</span>'


def seed_files():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({
            "site_name": "Smart Finds Review",
            "site_base_url": "https://tudominio.com",
            "amazon_tag": "TU-TAG-20",
            "author_name": "Edwin Sumaran",
            "author_full_name": "Edwin Ramon Sumaran Ojeda",
            "author_email": "edwinsumaran3@gmail.com",
            "author_bio": "Product reviewer and content creator focused on practical solutions for everyday problems.",
            "disclosure": "As an Amazon Associate, I earn from qualifying purchases.",
            "daily_video_cap": 20,
            "max_active_products": 5,
            "tracking_endpoint": "http://localhost:5055/track"
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    if not PRODUCTS_PATH.exists():
        PRODUCTS_PATH.write_text(json.dumps([
            {"active": True, "product_name": "Portable Mini Blender", "category": "Kitchen", "niche": "kitchen", "problem": "making healthy drinks is hard when you are busy", "who_it_is_for": "busy people who want quick smoothies at home, work, or while traveling", "primary_keyword": "portable mini blender review", "secondary_keywords": ["mini blender for smoothies", "portable blender for travel"], "amazon_keyword": "portable mini blender", "amazon_asin": "", "competitor_1": "Traditional countertop blender", "competitor_2": "Manual shaker bottle", "status": "active"},
            {"active": True, "product_name": "Car Seat Gap Organizer", "category": "Automotive", "niche": "car", "problem": "small things fall between your car seats every day", "who_it_is_for": "drivers who want a cleaner car and easier access to phone, keys, cards, and small items", "primary_keyword": "car seat gap organizer review", "secondary_keywords": ["car organizer between seats", "seat gap filler organizer"], "amazon_keyword": "car seat gap organizer", "amazon_asin": "", "competitor_1": "Basic seat gap filler", "competitor_2": "Console storage box", "status": "active"},
            {"active": True, "product_name": "Kitchen Food Saver Gadget", "category": "Kitchen", "niche": "kitchen", "problem": "people waste food because storage is messy", "who_it_is_for": "families and home cooks who want to keep food organized and reduce waste", "primary_keyword": "kitchen food saver gadget review", "secondary_keywords": ["food storage gadget", "kitchen storage tool"], "amazon_keyword": "kitchen food saver gadget", "amazon_asin": "", "competitor_1": "Standard food containers", "competitor_2": "Reusable storage bags", "status": "active"},
            {"active": True, "product_name": "Home Cable Organizer", "category": "Home", "niche": "home", "problem": "cables make desks and rooms look messy", "who_it_is_for": "people who want a cleaner workspace or gaming setup", "primary_keyword": "home cable organizer review", "secondary_keywords": ["desk cable organizer", "cable management box"], "amazon_keyword": "home cable organizer", "amazon_asin": "", "competitor_1": "Cable ties", "competitor_2": "Cable management box", "status": "active"},
            {"active": True, "product_name": "Mini Vacuum Cleaner", "category": "Home", "niche": "home", "problem": "small dust and crumbs are hard to clean quickly", "who_it_is_for": "people who want a quick cleaning tool for desk, car or small spaces", "primary_keyword": "mini vacuum cleaner review", "secondary_keywords": ["small vacuum for desk", "portable vacuum cleaner"], "amazon_keyword": "mini vacuum cleaner", "amazon_asin": "", "competitor_1": "Regular vacuum", "competitor_2": "Cleaning cloth", "status": "active"}
        ], indent=2, ensure_ascii=False), encoding="utf-8")

    if not ACCOUNTS_PATH.exists():
        ACCOUNTS_PATH.write_text(json.dumps([
            {"account_name": "kitchen_yt_1", "platform": "YouTube Shorts", "niche": "kitchen", "daily_limit": 3, "status": "active"},
            {"account_name": "kitchen_tiktok_1", "platform": "TikTok", "niche": "kitchen", "daily_limit": 3, "status": "active"},
            {"account_name": "car_tiktok_1", "platform": "TikTok", "niche": "car", "daily_limit": 3, "status": "active"},
            {"account_name": "home_pinterest_1", "platform": "Pinterest", "niche": "home", "daily_limit": 4, "status": "active"},
            {"account_name": "home_yt_1", "platform": "YouTube Shorts", "niche": "home", "daily_limit": 3, "status": "active"}
        ], indent=2, ensure_ascii=False), encoding="utf-8")


def config():
    seed_files()
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(data):
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def products_json():
    seed_files()
    return json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))


def save_products(data):
    PRODUCTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def accounts_json():
    seed_files()
    return json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))


def save_accounts(data):
    ACCOUNTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    c = conn()
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, product_name TEXT UNIQUE, category TEXT, niche TEXT, problem TEXT, keyword TEXT, status TEXT DEFAULT 'active', created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, account_name TEXT UNIQUE, platform TEXT, niche TEXT, daily_limit INTEGER DEFAULT 3, status TEXT DEFAULT 'active', created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS variants (id TEXT PRIMARY KEY, product_name TEXT, variant_name TEXT, hook TEXT, script TEXT, platform TEXT, account_name TEXT, status TEXT DEFAULT 'testing', views INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, sales INTEGER DEFAULT 0, commission REAL DEFAULT 0, ctr REAL DEFAULT 0, conversion_rate REAL DEFAULT 0, epm REAL DEFAULT 0, decision TEXT DEFAULT '', created_at TEXT, updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS publish_queue (id TEXT PRIMARY KEY, product_name TEXT, variant_id TEXT, account_name TEXT, platform TEXT, scheduled_time TEXT, status TEXT DEFAULT 'ready_to_post', caption TEXT, video_path TEXT, article_path TEXT DEFAULT '', posted_url TEXT DEFAULT '', created_at TEXT, updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, product_name TEXT, variant_id TEXT, decision TEXT, reason TEXT, action_plan TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tracking_events (id TEXT PRIMARY KEY, product_name TEXT, source TEXT, event_type TEXT, page_url TEXT, referrer TEXT, user_agent TEXT, created_at TEXT)""")
    c.commit()
    c.close()


def execute(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    c.commit()
    c.close()


def fetchall(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    c.close()
    return rows


def seed_db():
    seed_files()
    c = conn()
    cur = c.cursor()
    for p in products_json():
        cur.execute("""INSERT OR IGNORE INTO products (id, product_name, category, niche, problem, keyword, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), p["product_name"], p.get("category",""), p.get("niche",""), p.get("problem",""), p.get("primary_keyword",""), p.get("status","active"), datetime.now().isoformat()))
    for a in accounts_json():
        cur.execute("""INSERT OR IGNORE INTO accounts (id, account_name, platform, niche, daily_limit, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), a["account_name"], a.get("platform",""), a.get("niche",""), int(a.get("daily_limit",3)), a.get("status","active"), datetime.now().isoformat()))
    c.commit()
    c.close()


def slugify(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "item"


def amazon_link(product):
    cfg = config()
    asin = (product.get("amazon_asin") or "").strip()
    if asin:
        return f"https://www.amazon.com/dp/{asin}/?tag={cfg['amazon_tag']}"
    q = (product.get("amazon_keyword") or product.get("product_name") or "").replace(" ", "+")
    return f"https://www.amazon.com/s?k={q}&tag={cfg['amazon_tag']}"


def get_products(active_only=False):
    if active_only:
        return fetchall("SELECT product_name, category, niche, problem, keyword, status FROM products WHERE status='active' ORDER BY product_name")
    return fetchall("SELECT product_name, category, niche, problem, keyword, status FROM products ORDER BY product_name")


def get_accounts(active_only=False):
    if active_only:
        return fetchall("SELECT account_name, platform, niche, daily_limit, status FROM accounts WHERE status='active' ORDER BY niche, account_name")
    return fetchall("SELECT account_name, platform, niche, daily_limit, status FROM accounts ORDER BY niche, account_name")


def get_variants(limit=1000):
    return fetchall("""SELECT id, product_name, variant_name, hook, platform, account_name, status, views, clicks, sales, commission, ctr, conversion_rate, epm, decision, created_at FROM variants ORDER BY product_name ASC, epm DESC, views DESC LIMIT ?""", (limit,))


def get_queue(limit=1000):
    return fetchall("""SELECT id, product_name, account_name, platform, scheduled_time, status, caption, video_path, article_path, posted_url, created_at FROM publish_queue ORDER BY scheduled_time ASC LIMIT ?""", (limit,))


def today_count(table, date_col="created_at", where="1=1"):
    return int(fetchall(f"SELECT COUNT(*) FROM {table} WHERE date({date_col})=? AND {where}", (date.today().isoformat(),))[0][0] or 0)


def metric_sum(col):
    return float(fetchall(f"SELECT COALESCE(SUM({col}),0) FROM variants")[0][0] or 0)


def get_winners():
    return fetchall("""SELECT product_name, variant_name, platform, account_name, views, clicks, sales, commission, ctr, epm, decision FROM variants WHERE sales > 0 OR commission > 0 OR (views >= 10000 AND ctr >= 2) ORDER BY commission DESC, epm DESC, views DESC""")


def daily_metrics():
    return {
        "posted_today": today_count("publish_queue", "updated_at", "status='posted'"),
        "queued_today": today_count("publish_queue", "created_at"),
        "variants_today": today_count("variants", "created_at"),
        "decisions_today": today_count("decisions", "created_at"),
        "winners": len(get_winners()),
        "views": int(metric_sum("views")),
        "clicks": int(metric_sum("clicks")),
        "sales": int(metric_sum("sales")),
        "commission": float(metric_sum("commission")),
        "tracking_events": today_count("tracking_events", "created_at"),
    }


def product_dict(name):
    for p in products_json():
        if p.get("product_name") == name:
            return p
    return {}


def make_script(product_name, hook, problem="Most people deal with this every day."):
    return f"""{hook}

Here is the problem:
{problem}

That is why I reviewed {product_name}.

It is not a magic product, but it can be useful if this problem bothers you.

Before buying, check the full review, pros, cons, and details on the site.

Full review is on the website.
"""


def make_caption(product_name, platform):
    tags = "#amazonfinds #productreview #smartfinds"
    if platform == "YouTube Shorts":
        tags += " #shorts"
    elif platform == "TikTok":
        tags += " #tiktokmademebuyit #viralfinds"
    elif platform == "Pinterest":
        tags += " #shoppingideas #productfinds"
    return f"I tested {product_name} because it solves a real everyday problem.\n\nFull review is on the site.\n\n{tags}"


def create_human_article(product):
    cfg = config()
    name = product.get("product_name", "Product")
    aff = amazon_link(product)
    secondary = ", ".join(product.get("secondary_keywords", []))
    return f"""<main>
<p class="disclosure"><strong>Disclosure:</strong> {escape(cfg['disclosure'])}</p>
<section class="card"><h1>{escape(name)} Review: Does it actually solve the problem?</h1><p><strong>Author:</strong> {escape(cfg['author_full_name'])} · Last updated {date.today()}</p><p>{escape(cfg['author_bio'])}</p></section>
<section class="card"><h2>Why I decided to review it</h2><p>I decided to look at <strong>{escape(name)}</strong> because the problem is common: {escape(product.get('problem',''))}.</p><p>Many products look useful in short videos, but not all of them make sense in real daily use. This review explains who this product is for, what it can realistically solve, and where it may fall short.</p></section>
<section class="card"><h2>Quick verdict</h2><p>{escape(name)} is worth considering if you are {escape(product.get('who_it_is_for','looking for a practical everyday product'))}.</p><p>It is not a magic product. It is useful only if the specific problem matters to you.</p><p><a class="btn" data-product="{escape(name)}" href="{escape(aff)}" target="_blank" rel="nofollow sponsored noopener">Check latest price on Amazon</a></p></section>
<section class="card"><h2>What I liked</h2><ul><li>It solves a clear everyday problem.</li><li>The use case is easy to understand.</li><li>It can save time or reduce frustration in the right situation.</li><li>It is easier to compare than many random gadgets online.</li></ul></section>
<section class="card"><h2>What I did not like</h2><ul><li>Quality may vary depending on the seller.</li><li>It may not be useful for everyone.</li><li>Some buyers may expect more than what the product can realistically deliver.</li><li>Price and availability can change, so checking recent reviews is important.</li></ul></section>
<section class="card"><h2>Who should buy this?</h2><p>This product makes sense for people who have the exact problem described above and want a simple solution without overcomplicating things.</p></section>
<section class="card"><h2>Who should avoid this?</h2><p>You should avoid it if you expect a premium solution, if you do not really have this problem, or if reviews show quality issues with the current seller.</p></section>
<section class="card"><h2>Comparison with alternatives</h2><table><tr><th>Option</th><th>Best for</th><th>Limitation</th></tr><tr><td>{escape(name)}</td><td>Specific problem solving</td><td>Depends on seller/model</td></tr><tr><td>{escape(product.get('competitor_1','Alternative'))}</td><td>Traditional users</td><td>Less specific</td></tr><tr><td>{escape(product.get('competitor_2','Basic option'))}</td><td>Budget users</td><td>May be less effective</td></tr></table></section>
<section class="card"><h2>SEO related searches</h2><p>Main keyword: <strong>{escape(product.get('primary_keyword',''))}</strong></p><p>Related terms: {escape(secondary)}</p></section>
<section class="card"><h2>FAQ</h2><h3>Is it worth buying?</h3><p>It can be worth buying if the problem is real for you and current Amazon reviews look positive.</p><h3>Should I compare alternatives?</h3><p>Yes. Always compare price, reviews, seller details, return policy and product photos.</p><h3>Is this an affiliate review?</h3><p>Yes. This site may earn from qualifying purchases as an Amazon Associate.</p></section>
<section class="card"><h2>Final verdict</h2><p>I would not call this a must-have for everyone. But if you deal with this specific problem regularly, it is worth comparing with alternatives.</p><p><a class="btn" data-product="{escape(name)}" href="{escape(aff)}" target="_blank" rel="nofollow sponsored noopener">See real reviews on Amazon</a></p></section>
</main>"""


def write_public_assets():
    (ASSETS / "style.css").write_text("""
:root{--bg:#f8fafc;--ink:#0f172a;--line:#e2e8f0;--accent:#f59e0b;--blue:#0a6ed1}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--ink);line-height:1.72}
header{background:linear-gradient(135deg,#0f172a,#164e63);color:white;padding:24px}nav a{color:white;margin-right:14px;text-decoration:none;font-weight:700}
main{max-width:1050px;margin:auto;padding:30px 18px}.card{background:white;border:1px solid var(--line);border-radius:18px;padding:22px;margin:18px 0;box-shadow:0 10px 28px rgba(15,23,42,.06)}
.btn{display:inline-block;background:var(--accent);color:#111827;padding:13px 18px;border-radius:12px;text-decoration:none;font-weight:800}.disclosure{background:#fff7ed;border:1px solid #fed7aa;padding:12px;border-radius:12px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}video{width:100%;border-radius:18px}footer{background:#0f172a;color:#cbd5e1;text-align:center;padding:28px}
table{width:100%;border-collapse:collapse}td,th{border:1px solid #e2e8f0;padding:10px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
""", encoding="utf-8")

    endpoint = config().get("tracking_endpoint", "http://localhost:5055/track")
    (ASSETS / "lca_tracker.js").write_text(f"""
(function(){{
  function sendEvent(eventType, productName){{
    try {{
      fetch("{endpoint}", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          event_type: eventType,
          product_name: productName || document.body.getAttribute("data-product") || "",
          source: new URLSearchParams(window.location.search).get("src") || document.referrer || "direct",
          page_url: window.location.href,
          referrer: document.referrer
        }})
      }});
    }} catch(e) {{}}
  }}
  window.LCATrack = sendEvent;
  document.addEventListener("DOMContentLoaded", function(){{
    sendEvent("page_view");
    document.querySelectorAll("a[href*='amazon.']").forEach(function(a){{
      a.addEventListener("click", function(){{
        sendEvent("amazon_click", a.getAttribute("data-product") || "");
      }});
    }});
  }});
}})();
""", encoding="utf-8")

    server_lines = [
        "from flask import Flask, request, jsonify\n",
        "from flask_cors import CORS\n",
        "import sqlite3, uuid\n",
        "from datetime import datetime\n\n",
        "app = Flask(__name__)\n",
        "CORS(app)\n",
        "DB_PATH = 'data/lca_pro_final.db'\n\n",
        "def init_db():\n",
        "    c = sqlite3.connect(DB_PATH)\n",
        "    cur = c.cursor()\n",
        "    cur.execute(\"\"\"CREATE TABLE IF NOT EXISTS tracking_events (id TEXT PRIMARY KEY, product_name TEXT, source TEXT, event_type TEXT, page_url TEXT, referrer TEXT, user_agent TEXT, created_at TEXT)\"\"\")\n",
        "    c.commit(); c.close()\n\n",
        "@app.route('/track', methods=['POST'])\n",
        "def track():\n",
        "    data = request.get_json(force=True) or {}\n",
        "    c = sqlite3.connect(DB_PATH)\n",
        "    cur = c.cursor()\n",
        "    cur.execute(\"\"\"INSERT INTO tracking_events (id, product_name, source, event_type, page_url, referrer, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)\"\"\", (str(uuid.uuid4()), data.get('product_name',''), data.get('source',''), data.get('event_type',''), data.get('page_url',''), data.get('referrer',''), request.headers.get('User-Agent',''), datetime.now().isoformat()))\n",
        "    c.commit(); c.close()\n",
        "    return jsonify({'ok': True})\n\n",
        "if __name__ == '__main__':\n",
        "    init_db()\n",
        "    app.run(host='0.0.0.0', port=5055)\n"
    ]
    (PUBLIC / "tracking_server_example.py").write_text("".join(server_lines), encoding="utf-8")


def shell(title, body, product_name=""):
    cfg = config()
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{escape(title)}</title><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/assets/style.css"></head><body data-product="{escape(product_name)}"><header><h1>{escape(cfg['site_name'])}</h1><nav><a href="/index.html">Home</a><a href="/blog/index.html">Blog</a><a href="/category/index.html">Categories</a><a href="/about.html">About</a><a href="/editorial-policy.html">Editorial</a><a href="/contact.html">Contact</a><a href="/affiliate-disclosure.html">Disclosure</a></nav></header>{body}<footer><p>{escape(cfg['disclosure'])}</p><p>Author: {escape(cfg['author_name'])}</p></footer><script src="/assets/lca_tracker.js"></script></body></html>"""


def write_legal_pages():
    cfg = config()
    pages = {
        "about.html": ("About", f"<main><section class='card'><h1>About {escape(cfg['site_name'])}</h1><p>Author: {escape(cfg['author_full_name'])}</p><p>{escape(cfg['author_bio'])}</p><p>This website publishes practical product reviews, comparisons and buying guides.</p></section></main>"),
        "contact.html": ("Contact", f"<main><section class='card'><h1>Contact</h1><p>{escape(cfg['author_email'])}</p></section></main>"),
        "privacy-policy.html": ("Privacy Policy", "<main><section class='card'><h1>Privacy Policy</h1><p>This website may collect basic analytics data such as visits, clicks, browser type and referral source. Third-party services including Amazon may use cookies when users click affiliate links.</p></section></main>"),
        "terms.html": ("Terms", "<main><section class='card'><h1>Terms and Conditions</h1><p>Content is for informational purposes only. Prices, availability, product details and seller details may change without notice.</p></section></main>"),
        "affiliate-disclosure.html": ("Affiliate Disclosure", f"<main><section class='card'><h1>Affiliate Disclosure</h1><p><strong>{escape(cfg['disclosure'])}</strong></p><p>This means this website may earn a commission from qualifying purchases at no extra cost to the reader.</p></section></main>"),
        "editorial-policy.html": ("Editorial Policy", "<main><section class='card'><h1>Editorial Policy</h1><p>We focus on practical use cases, comparison with alternatives, limitations and buying considerations. Readers should verify current price, seller, reviews and return policy before purchasing.</p></section></main>"),
        "how-we-review.html": ("How We Review Products", "<main><section class='card'><h1>How We Review Products</h1><p>We evaluate products based on problem solved, usability, buyer fit, alternatives, pros, cons and everyday value.</p></section></main>"),
        "cookie-policy.html": ("Cookie Policy", "<main><section class='card'><h1>Cookie Policy</h1><p>This site may use cookies for analytics and affiliate tracking. Third-party websites may use their own cookies.</p></section></main>"),
        "dmca.html": ("DMCA / Copyright", f"<main><section class='card'><h1>DMCA / Copyright</h1><p>For copyright concerns, contact: {escape(cfg['author_email'])}</p></section></main>")
    }
    for filename, (title, body) in pages.items():
        (PUBLIC / filename).write_text(shell(title, body), encoding="utf-8")


def generate_site():
    write_public_assets()
    write_legal_pages()
    products = [p for p in products_json() if p.get("active", True) and p.get("status", "active") == "active"]
    cards = ""
    categories = {}
    urls = ["/index.html","/blog/index.html","/category/index.html","/about.html","/contact.html","/privacy-policy.html","/terms.html","/affiliate-disclosure.html","/editorial-policy.html","/how-we-review.html","/cookie-policy.html","/dmca.html"]

    for p in products:
        slug = slugify(p.get("primary_keyword") or p["product_name"])
        article = create_human_article(p)
        (BLOG / f"{slug}.html").write_text(shell(f"{p['product_name']} Review", article, p["product_name"]), encoding="utf-8")
        cards += f'<div class="card"><h2>{escape(p["product_name"])}</h2><p>{escape(p.get("problem",""))}</p><a class="btn" href="/blog/{slug}.html">Read review</a></div>'
        categories.setdefault(p.get("category","General"), []).append(p)
        urls.append(f"/blog/{slug}.html")

    (BLOG / "index.html").write_text(shell("Blog", f"<main><h1>Blog</h1><div class='grid'>{cards}</div></main>"), encoding="utf-8")
    (PUBLIC / "index.html").write_text(shell("Home", f"<main><h1>Smart product reviews</h1><p>We review practical products that solve everyday problems. Our goal is to help you choose what actually works — not just what looks good online.</p><div class='grid'>{cards}</div></main>"), encoding="utf-8")

    category_cards = ""
    for cat, plist in categories.items():
        cat_slug = slugify(cat)
        category_cards += f"<div class='card'><h2>{escape(cat)}</h2><p>{len(plist)} reviews</p><a class='btn' href='/category/{cat_slug}.html'>Open category</a></div>"
        item_cards = ""
        for p in plist:
            slug = slugify(p.get("primary_keyword") or p["product_name"])
            item_cards += f"<div class='card'><h2>{escape(p['product_name'])}</h2><p>{escape(p.get('problem',''))}</p><a class='btn' href='/blog/{slug}.html'>Read</a></div>"
        (CATEGORY / f"{cat_slug}.html").write_text(shell(f"{cat} Reviews", f"<main><h1>{escape(cat)}</h1><div class='grid'>{item_cards}</div></main>"), encoding="utf-8")
        urls.append(f"/category/{cat_slug}.html")
    (CATEGORY / "index.html").write_text(shell("Categories", f"<main><h1>Categories</h1><div class='grid'>{category_cards}</div></main>"), encoding="utf-8")

    base_url = config()["site_base_url"].rstrip("/")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml.append(f"<url><loc>{base_url}{url}</loc><lastmod>{date.today().isoformat()}</lastmod></url>")
    xml.append("</urlset>")
    (PUBLIC / "sitemap.xml").write_text("\n".join(xml), encoding="utf-8")
    (PUBLIC / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n", encoding="utf-8")
    return len(products)


def ffmpeg_ok():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def find_font():
    for p in ["C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/segoeuib.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(p).exists():
            return p
    return None


def split_captions(script, max_chars=48):
    clean = re.sub(r"\s+", " ", script.strip())
    parts = re.split(r"(?<=[.!?])\s+", clean)
    captions = []
    for p in parts:
        if p.strip():
            captions.extend(textwrap.wrap(p.strip(), width=max_chars))
    return captions[:14] or ["Full review on the site."]


def make_frame(text, product_name, idx, total, out_path):
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), "#0f172a")
    draw = ImageDraw.Draw(img)
    for y in range(H):
        shade = int(14 + (y / H) * 38)
        draw.line([(0, y), (W, y)], fill=(shade, 35 + int(y / H * 45), 64 + int(y / H * 55)))
    fp = find_font()
    small = ImageFont.truetype(fp, 34) if fp else ImageFont.load_default()
    mid = ImageFont.truetype(fp, 54) if fp else ImageFont.load_default()
    big = ImageFont.truetype(fp, 76) if fp else ImageFont.load_default()
    draw.rounded_rectangle((55,55,W-55,205), radius=32, fill="#111827", outline="#334155", width=3)
    draw.text((90,88), "LCA SMART FINDS", font=small, fill="#e5e7eb")
    draw.text((90,132), product_name[:36], font=small, fill="#fbbf24")
    draw.rounded_rectangle((70,500,W-70,1310), radius=46, fill="#ffffff", outline="#e2e8f0", width=4)
    y = 610
    for line in textwrap.wrap(text, width=22)[:7]:
        box = draw.textbbox((0,0), line, font=big)
        draw.text(((W-(box[2]-box[0]))/2, y), line, font=big, fill="#0f172a")
        y += 90
    draw.rounded_rectangle((90,1480,W-90,1645), radius=34, fill="#f59e0b")
    cta = "Full review on the site"
    box = draw.textbbox((0,0), cta, font=mid)
    draw.text(((W-(box[2]-box[0]))/2,1536), cta, font=mid, fill="#111827")
    img.save(out_path)


def create_video(product_name, script, seconds_per_caption=2.4):
    if not ffmpeg_ok():
        raise RuntimeError("FFmpeg no está instalado o no está en PATH.")
    job = str(uuid.uuid4())[:8]
    frame_dir = FRAMES / job
    frame_dir.mkdir(parents=True, exist_ok=True)
    captions = split_captions(script)
    paths = []
    for i, cap in enumerate(captions):
        fp = frame_dir / f"frame_{i:03d}.png"
        make_frame(cap, product_name, i, len(captions), fp)
        paths.append(fp)
    list_file = frame_dir / "frames.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")
            f.write(f"duration {seconds_per_caption}\n")
        f.write(f"file '{paths[-1].resolve().as_posix()}'\n")
    out = VIDEOS / f"{slugify(product_name)}_{job}.mp4"
    cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",str(list_file),"-vf","format=yuv420p","-r","30","-c:v","libx264","-pix_fmt","yuv420p",str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    return str(out)


def create_ab_variants(product_name, niche, count=3):
    p = product_dict(product_name)
    problem = p.get("problem", "Most people deal with this every day.")
    accounts = [a for a in get_accounts(True) if a[2] == niche]
    if not accounts:
        return 0
    c = conn()
    cur = c.cursor()
    created = 0
    for i in range(int(count)):
        hook = VIRAL_HOOKS[(i + len(get_variants())) % len(VIRAL_HOOKS)]
        account_name, platform, _, _, _ = accounts[i % len(accounts)]
        variant_name = f"{product_name} - Variant {i+1}-{str(uuid.uuid4())[:4]}"
        script = make_script(product_name, hook, problem)
        cur.execute("""INSERT INTO variants (id, product_name, variant_name, hook, script, platform, account_name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), product_name, variant_name, hook, script, platform, account_name, "testing", datetime.now().isoformat(), datetime.now().isoformat()))
        created += 1
    c.commit()
    c.close()
    return created


def create_all_ab_tests(count=3):
    total = 0
    for product_name, category, niche, problem, keyword, status in get_products(True):
        total += create_ab_variants(product_name, niche, count)
    return total


def next_slot(start=None):
    now = start or datetime.now()
    for h in DEFAULT_SLOTS:
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    return (now + timedelta(days=1)).replace(hour=DEFAULT_SLOTS[0], minute=0, second=0, microsecond=0)


def account_posts_today(account_name):
    return int(fetchall("SELECT COUNT(*) FROM publish_queue WHERE account_name=? AND date(scheduled_time)=?", (account_name, date.today().isoformat()))[0][0] or 0)


def enqueue_variant(row, video_path="", article_path=""):
    variant_id, product, variant, hook, platform, account_name, status, views, clicks, sales, commission, ctr, conv, epm, decision, created = row
    if not account_name:
        return False
    acc = fetchall("SELECT daily_limit FROM accounts WHERE account_name=?", (account_name,))
    daily_limit = int(acc[0][0]) if acc else 3
    if account_posts_today(account_name) >= daily_limit:
        return False
    if today_count("publish_queue") >= int(config().get("daily_video_cap", 20)):
        return False
    last = fetchall("SELECT scheduled_time FROM publish_queue WHERE account_name=? ORDER BY scheduled_time DESC LIMIT 1", (account_name,))
    base = datetime.now()
    if last:
        try:
            base = datetime.fromisoformat(last[0][0]) + timedelta(hours=3)
        except Exception:
            pass
    scheduled = next_slot(base)
    execute("""INSERT INTO publish_queue (id, product_name, variant_id, account_name, platform, scheduled_time, status, caption, video_path, article_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (str(uuid.uuid4()), product, variant_id, account_name, platform, scheduled.isoformat(), "ready_to_post", make_caption(product, platform), video_path, article_path, datetime.now().isoformat(), datetime.now().isoformat()))
    return True


def enqueue_testing_variants():
    q, s = 0, 0
    for row in get_variants():
        if row[6] in ["testing", "scaled", ""]:
            if enqueue_variant(row):
                q += 1
            else:
                s += 1
    return q, s


def update_variant_metrics(product_name, platform, views, clicks, sales, commission, variant_name=""):
    if variant_name:
        row = fetchall("SELECT id, views, clicks, sales, commission FROM variants WHERE product_name=? AND platform=? AND variant_name=? ORDER BY created_at ASC LIMIT 1", (product_name, platform, variant_name))
    else:
        row = fetchall("SELECT id, views, clicks, sales, commission FROM variants WHERE product_name=? AND platform=? ORDER BY created_at ASC LIMIT 1", (product_name, platform))
    if not row:
        hook = "Imported hook"
        execute("""INSERT INTO variants (id, product_name, variant_name, hook, script, platform, account_name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), product_name, variant_name or f"{product_name} imported", hook, make_script(product_name, hook), platform, "", "testing", datetime.now().isoformat(), datetime.now().isoformat()))
        row = fetchall("SELECT id, views, clicks, sales, commission FROM variants WHERE product_name=? AND platform=? ORDER BY created_at DESC LIMIT 1", (product_name, platform))
    vid, ov, oc, os, ocomm = row[0]
    nv = int(ov or 0) + int(views or 0)
    nc = int(oc or 0) + int(clicks or 0)
    ns = int(os or 0) + int(sales or 0)
    ncomm = float(ocomm or 0) + float(commission or 0)
    ctr = (nc / nv * 100) if nv else 0
    conv = (ns / nc * 100) if nc else 0
    epm = (ncomm / nv * 1000) if nv else 0
    execute("UPDATE variants SET views=?, clicks=?, sales=?, commission=?, ctr=?, conversion_rate=?, epm=?, updated_at=? WHERE id=?", (nv, nc, ns, ncomm, ctr, conv, epm, datetime.now().isoformat(), vid))


def import_metrics_csv(uploaded):
    raw = uploaded.getvalue().decode("utf-8-sig")
    reader = csv.DictReader(raw.splitlines())
    required = ["product_name", "platform", "views", "clicks", "sales", "commission"]
    if not reader.fieldnames:
        raise ValueError("CSV vacío o sin encabezados.")
    missing = [x for x in required if x not in reader.fieldnames]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}. Requeridas: {required}")
    count = 0
    for r in reader:
        update_variant_metrics(r.get("product_name","").strip(), r.get("platform","").strip(), int(float(r.get("views",0) or 0)), int(float(r.get("clicks",0) or 0)), int(float(r.get("sales",0) or 0)), float(r.get("commission",0) or 0), r.get("variant_name","").strip())
        count += 1
    return count


def decide(row):
    vid, product, variant, hook, platform, account, status, views, clicks, sales, commission, ctr, conv, epm, decision, created = row
    views = int(views or 0)
    clicks = int(clicks or 0)
    sales = int(sales or 0)
    commission = float(commission or 0)
    ctr = float(ctr or 0)
    if sales >= 2 or commission >= 5:
        return "SCALE_HARD 💰", "Ventas/comisión real. Escalar agresivo."
    if sales >= 1 or commission > 0:
        return "SCALE 💰", "Ya generó venta o comisión."
    if views >= 10000 and ctr >= 2:
        return "SCALE_TRAFFIC 🚀", "Tráfico alto y buen CTR."
    if views >= 3000 and ctr < 1:
        return "FIX_HOOK ⚠️", "Hay views pero pocos clics."
    if views < 500:
        return "NEW_ANGLE 🔁", "Pocas views."
    if clicks >= 30 and sales == 0:
        return "FIX_OFFER 🧪", "Hay clics pero no ventas."
    return "KEEP 📌", "Seguir midiendo."


def action_plan(decision, product):
    if "SCALE_HARD" in decision:
        return f"Crear 6 variantes nuevas para {product}; publicar 3–5 videos diarios por 3 días."
    if "SCALE" in decision:
        return f"Crear 3 variantes nuevas para {product}; publicar en 2 plataformas adicionales."
    if "FIX_HOOK" in decision:
        return "Cambiar primeros 2 segundos, problema más directo y hook before/after."
    if "FIX_OFFER" in decision:
        return "Revisar botones Amazon, alternativas, reviews y precio."
    if "NEW_ANGLE" in decision:
        return "Cambiar ángulo creativo y probar otra plataforma."
    return "Mantener en observación."


def run_decisions():
    rows = get_variants()
    c = conn()
    cur = c.cursor()
    n = 0
    for row in rows:
        vid = row[0]
        product = row[1]
        d, reason = decide(row)
        plan = action_plan(d, product)
        cur.execute("UPDATE variants SET decision=?, updated_at=? WHERE id=?", (d, datetime.now().isoformat(), vid))
        cur.execute("INSERT INTO decisions (id, product_name, variant_id, decision, reason, action_plan, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), product, vid, d, reason, plan, datetime.now().isoformat()))
        n += 1
    c.commit()
    c.close()
    return n


def get_decisions(limit=100):
    return fetchall("SELECT product_name, decision, reason, action_plan, created_at FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,))


def scale_winners():
    created = 0
    for w in get_winners():
        product = w[0]
        sales = int(w[6] or 0)
        commission = float(w[7] or 0)
        p = product_dict(product)
        created += create_ab_variants(product, p.get("niche",""), 6 if sales >= 2 or commission >= 5 else 3)
    q, s = enqueue_testing_variants()
    return created, q, s


def auto_mode_total():
    result = {"articles_created": 0, "videos_created": 0, "variants_created": 0, "queued": 0, "skipped": 0, "site_updated": False, "decisions": 0, "scaled": 0, "errors": []}
    active_products = [p for p in products_json() if p.get("active", True) and p.get("status", "active") == "active"]
    try:
        result["articles_created"] = generate_site()
        result["site_updated"] = True
    except Exception as e:
        result["errors"].append(f"web: {e}")
    try:
        result["variants_created"] = create_all_ab_tests(3)
    except Exception as e:
        result["errors"].append(f"variants: {e}")
    for p in active_products[:3]:
        try:
            script = make_script(p["product_name"], VIRAL_HOOKS[0], p.get("problem",""))
            video_path = create_video(p["product_name"], script) if ffmpeg_ok() else ""
            if video_path:
                result["videos_created"] += 1
        except Exception as e:
            result["errors"].append(f"video {p.get('product_name')}: {e}")
    try:
        q, s = enqueue_testing_variants()
        result["queued"] += q
        result["skipped"] += s
    except Exception as e:
        result["errors"].append(f"queue: {e}")
    try:
        result["decisions"] = run_decisions()
        created, queued, skipped = scale_winners()
        result["scaled"] = created
        result["queued"] += queued
        result["skipped"] += skipped
    except Exception as e:
        result["errors"].append(f"money: {e}")
    return result


def create_templates():
    social = EXPORTS / "metrics_template.csv"
    with open(social, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_name","platform","variant_name","views","clicks","sales","commission"])
        w.writerow(["Portable Mini Blender","TikTok","Portable Mini Blender - Variant 1","4500","55","0","0"])
    return social


def export_queue_csv():
    out = EXPORTS / "agency_publish_queue.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id","product_name","account_name","platform","scheduled_time","status","caption","video_path","article_path","posted_url"])
        for r in get_queue(10000):
            w.writerow(r[:10])
    return out


def zip_public_site():
    generate_site()
    out = EXPORTS / "public_site_ready.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in PUBLIC.rglob("*"):
            if f.is_file():
                z.write(f, arcname=str(f.relative_to(PUBLIC)))
    return out


def to_df_variants():
    return pd.DataFrame(get_variants(), columns=["ID","Producto","Variante","Hook","Plataforma","Cuenta","Estado","Views","Clicks","Ventas","Comisión","CTR","Conv","EPM","Decisión","Fecha"])


def platform_upload_url(platform):
    if platform == "YouTube Shorts":
        return "https://studio.youtube.com/"
    if platform == "TikTok":
        return "https://www.tiktok.com/upload"
    if platform == "Pinterest":
        return "https://www.pinterest.com/pin-builder/"
    return ""


def action_center():
    st.markdown('<div class="action-bar">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    if c1.button("🚀 AUTO TOTAL", use_container_width=True, key="top_auto_total"):
        st.session_state["last_action"] = auto_mode_total()
    if c2.button("🧪 Crear A/B", use_container_width=True, key="top_ab"):
        st.session_state["last_action"] = {"created": create_all_ab_tests(3)}
    if c3.button("📤 Encolar", use_container_width=True, key="top_queue"):
        q,s = enqueue_testing_variants()
        st.session_state["last_action"] = {"queued": q, "skipped": s}
    if c4.button("🧠 Analizar", use_container_width=True, key="top_decide"):
        st.session_state["last_action"] = {"decisions": run_decisions()}
    if c5.button("💰 Escalar", use_container_width=True, key="top_scale"):
        created, queued, skipped = scale_winners()
        st.session_state["last_action"] = {"created": created, "queued": queued, "skipped": skipped}
    if c6.button("🌐 Web", use_container_width=True, key="top_web"):
        st.session_state["last_action"] = {"site_products": generate_site()}
    st.markdown('</div>', unsafe_allow_html=True)
    if "last_action" in st.session_state:
        st.json(st.session_state["last_action"])


def dashboard_page():
    header("🏢 LCA PRO FINAL ÚNICA", "Contenido + blog + video + analytics + money engine")
    m = daily_metrics()
    score = min(100, min(m["posted_today"],5)*8 + min(m["variants_today"],3)*10 + min(m["decisions_today"],2)*10 + (20 if m["winners"] else 0))
    cols = st.columns(6)
    with cols[0]: kpi("Comisión", f"${m['commission']:.2f}", "Acumulada")
    with cols[1]: kpi("Views", f"{m['views']:,}", "Total")
    with cols[2]: kpi("Clicks", f"{m['clicks']:,}", "Total")
    with cols[3]: kpi("Ventas", m["sales"], "Total")
    with cols[4]: kpi("Ganadores", m["winners"], "Detectados")
    with cols[5]: kpi("Score", f"{score}/100", "Ejecución")
    action_center()
    if m["commission"] > 0:
        st.markdown('<div class="alert-good">💰 Ingresos detectados. Escala productos ganadores.</div>', unsafe_allow_html=True)
    elif m["posted_today"] < 3:
        st.markdown('<div class="alert-warn">⚠️ Publicaciones bajas. El sistema necesita datos reales.</div>', unsafe_allow_html=True)
    st.subheader("🔥 Ganadores")
    winners = get_winners()
    if not winners:
        st.info("Aún no hay ganadores. Crea variantes, publica, importa métricas y analiza.")
    for w in winners:
        product, variant, platform, account, views, clicks, sales, commission, ctr, epm, decision = w
        with st.container(border=True):
            a,b,c,d,e = st.columns(5)
            a.write(f"### {product}")
            b.metric("Views", int(views or 0))
            c.metric("CTR", f"{float(ctr or 0):.2f}%")
            d.metric("Ventas", int(sales or 0))
            e.metric("Comisión", f"${float(commission or 0):.2f}")
            st.markdown(pill(decision), unsafe_allow_html=True)


def checklist_page():
    header("✅ Checklist Diario", "Disciplina operativa")
    m = daily_metrics()
    tasks = [("Crear variantes A/B", m["variants_today"], 3), ("Encolar contenido", m["queued_today"], 5), ("Publicar videos", m["posted_today"], 5), ("Importar/tracking", m["tracking_events"] + m["views"], 1), ("Analizar decisiones", m["decisions_today"], 1), ("Detectar ganador", m["winners"], 1), ("Generar clicks", m["clicks"], 1)]
    done = sum(1 for _, val, target in tasks if val >= target)
    st.progress(done / len(tasks))
    c1,c2,c3 = st.columns(3)
    c1.metric("Progreso", f"{done}/{len(tasks)}")
    c2.metric("Score", f"{int(done/len(tasks)*100)}/100")
    c3.metric("Comisión", f"${m['commission']:.2f}")
    for name, val, target in tasks:
        with st.container(border=True):
            a,b,c = st.columns([3,1,1])
            a.write(("✅ " if val >= target else "❌ ") + f"**{name}**")
            b.metric("Actual", val)
            c.metric("Meta", target)
    action_center()


def web_page():
    header("🌐 Web Afiliada", "Amazon ready: artículos, legal, SEO")
    c1,c2,c3 = st.columns(3)
    if c1.button("🌐 Generar web pública", use_container_width=True):
        st.success(f"Web generada con {generate_site()} productos.")
    if c2.button("📦 ZIP public_site", use_container_width=True):
        out = zip_public_site()
        st.success(f"ZIP creado: {out}")
    if c3.button("👁️ Preview", use_container_width=True):
        generate_site()
    st.code(str(PUBLIC.resolve()))
    st.code("Tracking local: python public_site/tracking_server_example.py")
    index = PUBLIC / "index.html"
    if index.exists():
        st.components.v1.html(index.read_text(encoding="utf-8"), height=650, scrolling=True)


def video_page():
    header("🎬 Video Automático", "MP4 vertical 9:16")
    if not ffmpeg_ok():
        st.warning("FFmpeg no detectado. Para video MP4 instala FFmpeg y verifica con: ffmpeg -version")
    products = get_products(True)
    if not products:
        st.info("No hay productos activos.")
        return
    selected = st.selectbox("Producto", [p[0] for p in products])
    row = [p for p in products if p[0] == selected][0]
    hook = st.selectbox("Hook viral", VIRAL_HOOKS)
    script = st.text_area("Script", value=make_script(row[0], hook, row[3]), height=260)
    seconds = st.slider("Segundos por subtítulo", 1.5, 4.0, 2.4, 0.1)
    if st.button("🎬 Generar MP4", use_container_width=True):
        try:
            out = create_video(selected, script, seconds)
            st.success(out)
            st.video(out)
        except Exception as e:
            st.error(str(e))
    for v in sorted(VIDEOS.glob("*.mp4"), reverse=True)[:10]:
        with st.container(border=True):
            st.write(v.name)
            st.video(str(v))
            st.download_button("Descargar MP4", v.read_bytes(), file_name=v.name, mime="video/mp4", key=f"dl_{v.name}")


def publish_page():
    header("📤 Publicación", "Cola semi automática")
    a,b = st.columns(2)
    if a.button("📥 Encolar variantes", use_container_width=True):
        q,s = enqueue_testing_variants()
        st.success(f"Encolados {q}, omitidos {s}.")
    if b.button("📄 Exportar cola CSV", use_container_width=True):
        out = export_queue_csv()
        st.success(f"Exportado: {out}")
    rows = get_queue()
    if not rows:
        st.info("Cola vacía.")
        return
    for r in rows:
        qid, product, account, platform, scheduled, status, caption, video_path, article_path, posted_url, created = r
        with st.container(border=True):
            a,b,c,d = st.columns(4)
            a.write(f"**{product}**")
            b.write(account)
            c.write(platform)
            d.markdown(pill(status), unsafe_allow_html=True)
            st.caption(f"Programado: {scheduled}")
            st.text_area("Caption", caption, key=f"cap_{qid}", height=110)
            link = platform_upload_url(platform)
            if link:
                st.link_button(f"📤 Abrir {platform}", link)
            url = st.text_input("URL publicada", value=posted_url or "", key=f"url_{qid}")
            c1,c2 = st.columns(2)
            if c1.button("✅ Marcar publicado", key=f"posted_{qid}", use_container_width=True):
                execute("UPDATE publish_queue SET status='posted', posted_url=?, updated_at=? WHERE id=?", (url, datetime.now().isoformat(), qid))
                st.rerun()
            if c2.button("⏳ Pendiente", key=f"pending_{qid}", use_container_width=True):
                execute("UPDATE publish_queue SET status='ready_to_post', updated_at=? WHERE id=?", (datetime.now().isoformat(), qid))
                st.rerun()


def analytics_page():
    header("📊 Analytics + Money Engine", "Métricas y decisiones")
    tab1, tab2, tab3 = st.tabs(["Tabla", "Importar CSV", "Decisiones"])
    with tab1:
        df = to_df_variants()
        if df.empty:
            st.info("No hay variantes.")
        else:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Views", int(df["Views"].sum()))
            c2.metric("Clicks", int(df["Clicks"].sum()))
            c3.metric("Ventas", int(df["Ventas"].sum()))
            c4.metric("Comisión", f"${float(df['Comisión'].sum()):.2f}")
            st.dataframe(df[["Producto","Variante","Plataforma","Cuenta","Views","Clicks","Ventas","Comisión","CTR","EPM","Decisión"]], use_container_width=True, hide_index=True)
    with tab2:
        if st.button("📄 Crear plantilla CSV"):
            st.success(f"Plantilla creada: {create_templates()}")
        tpl = EXPORTS / "metrics_template.csv"
        if tpl.exists():
            st.download_button("⬇️ Descargar plantilla", tpl.read_bytes(), file_name="metrics_template.csv")
        up = st.file_uploader("Subir CSV de métricas", type=["csv"])
        if up:
            try:
                st.success(f"{import_metrics_csv(up)} filas importadas.")
            except Exception as e:
                st.error(str(e))
    with tab3:
        if st.button("🧠 Analizar decisiones", use_container_width=True):
            st.success(f"{run_decisions()} decisiones generadas.")
        for d in get_decisions():
            product, decision, reason, plan, created = d
            with st.container(border=True):
                st.write(f"### {product}")
                st.markdown(pill(decision), unsafe_allow_html=True)
                st.caption(reason)
                st.code(plan)
                st.caption(created)


def growth_page():
    header("🔥 Crecimiento Viral", "Hooks, scripts y escala")
    products = get_products(True)
    if not products:
        st.info("No hay productos activos.")
        return
    selected = st.selectbox("Producto", [p[0] for p in products])
    p = product_dict(selected)
    for i, hook in enumerate(VIRAL_HOOKS):
        with st.container(border=True):
            st.write(f"**{i+1}. {hook}**")
            st.code(make_script(selected, hook, p.get("problem","")))
    c1,c2,c3 = st.columns(3)
    if c1.button("🧪 Crear 5 hooks A/B", use_container_width=True):
        st.success(f"{create_ab_variants(selected, p.get('niche',''), 5)} variantes creadas.")
    if c2.button("📤 Encolar variantes", use_container_width=True):
        q,s = enqueue_testing_variants()
        st.success(f"Encolados {q}, omitidos {s}.")
    if c3.button("💰 Escalar ganadores", use_container_width=True):
        created, q, s = scale_winners()
        st.success(f"Creados {created}, encolados {q}, omitidos {s}.")


def products_page():
    header("🛒 Productos")
    df = pd.DataFrame(get_products(), columns=["Producto","Categoría","Nicho","Problema","Keyword","Estado"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    txt = PRODUCTS_PATH.read_text(encoding="utf-8")
    edited = st.text_area("products.json", txt, height=360)
    if st.button("Guardar productos"):
        try:
            data = json.loads(edited)
            save_products(data)
            seed_db()
            st.success("Productos guardados.")
        except Exception as e:
            st.error(str(e))


def accounts_page():
    header("👥 Cuentas")
    df = pd.DataFrame(get_accounts(), columns=["Cuenta","Plataforma","Nicho","Límite diario","Estado"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    txt = ACCOUNTS_PATH.read_text(encoding="utf-8")
    edited = st.text_area("accounts.json", txt, height=300)
    if st.button("Guardar cuentas"):
        try:
            data = json.loads(edited)
            save_accounts(data)
            seed_db()
            st.success("Cuentas guardadas.")
        except Exception as e:
            st.error(str(e))


def settings_page():
    header("⚙️ Configuración")
    cfg = config()
    edited = {}
    for k, v in cfg.items():
        if isinstance(v, int):
            edited[k] = st.number_input(k, value=int(v))
        elif k in ["author_bio", "disclosure"]:
            edited[k] = st.text_area(k, value=str(v))
        else:
            edited[k] = st.text_input(k, value=str(v))
    st.warning("No publiques DNI. Para Amazon usa nombre, correo, bio, disclosure y dominio público.")
    if st.button("Guardar configuración", use_container_width=True):
        save_config(edited)
        st.success("Configuración guardada.")


def main():
    st.set_page_config(page_title=APP_NAME, page_icon="🏢", layout="wide")
    inject_css()
    init_db()
    seed_db()
    with st.sidebar:
        st.markdown("## 🏢 LCA PRO FINAL")
        st.caption("Versión única PRO")
        page = st.radio("Navegación", ["Dashboard","Checklist","Web Afiliada","Video","Publicación","Analytics","Crecimiento Viral","Productos","Cuentas","Configuración"])
        st.divider()
        m = daily_metrics()
        st.metric("Comisión", f"${m['commission']:.2f}")
        st.metric("Ganadores", m["winners"])
        st.metric("Publicados hoy", m["posted_today"])
    if page == "Dashboard":
        dashboard_page()
    elif page == "Checklist":
        checklist_page()
    elif page == "Web Afiliada":
        web_page()
    elif page == "Video":
        video_page()
    elif page == "Publicación":
        publish_page()
    elif page == "Analytics":
        analytics_page()
    elif page == "Crecimiento Viral":
        growth_page()
    elif page == "Productos":
        products_page()
    elif page == "Cuentas":
        accounts_page()
    elif page == "Configuración":
        settings_page()


if __name__ == "__main__":
    main()
