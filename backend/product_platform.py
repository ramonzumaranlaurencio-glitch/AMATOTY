import hashlib
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import uuid
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone
from functools import wraps
from io import BytesIO
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    import cloudinary
    import cloudinary.uploader
    _CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
    _CLD_CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    _CLD_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    _CLD_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
    if _CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=_CLOUDINARY_URL)
        _USE_CLOUDINARY = True
    elif _CLD_CLOUD and _CLD_KEY and _CLD_SECRET:
        cloudinary.config(cloud_name=_CLD_CLOUD, api_key=_CLD_KEY, api_secret=_CLD_SECRET, secure=True)
        _USE_CLOUDINARY = True
    else:
        # Última opción: verificar si ya está configurado (ej. variable de entorno del sistema)
        try:
            cfg = cloudinary.config()
            _USE_CLOUDINARY = bool(cfg.cloud_name and cfg.api_key and cfg.api_secret)
        except Exception:
            _USE_CLOUDINARY = False
except ImportError:
    _USE_CLOUDINARY = False


def _cloudinary_upload(raw: bytes, public_id: str, resource_type: str = "image") -> str:
    """Sube bytes a Cloudinary y devuelve la URL segura."""
    try:
        result = cloudinary.uploader.upload(
            BytesIO(raw),
            public_id=public_id,
            resource_type=resource_type,
            overwrite=True,
            use_filename=False,
        )
        return result["secure_url"]
    except Exception as cld_exc:
        raise RuntimeError(f"Cloudinary: {cld_exc}") from cld_exc


def _cloudinary_delete(public_id: str, resource_type: str = "image") -> None:
    """Elimina un recurso de Cloudinary sin lanzar excepcion si no existe."""
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception:
        pass


platform_bp = Blueprint("product_platform", __name__, url_prefix="/api/platform")

BASE_DIR = Path(__file__).resolve().parent.parent

# Permite usar un disco persistente en Render/Railway/etc.
# Ej: DATA_DIR=/var/data  UPLOAD_DIR=/var/data/uploads
_DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
_UPLOAD_DIR_ENV = os.environ.get("UPLOAD_DIR", "")

DB_PATH = _DATA_DIR / "lca_pro_final.db"
UPLOAD_DIR = Path(_UPLOAD_DIR_ENV) if _UPLOAD_DIR_ENV else BASE_DIR / "Productos"
PUBLIC_UPLOAD_PREFIX = "Productos"

TOKEN_TTL_DAYS = 14
RESET_TTL_MINUTES = 45
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime"}
WRITE_ROLES = {"owner", "admin", "editor"}
MANAGE_ROLES = {"owner", "admin"}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def make_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def normalize_email(email):
    return str(email or "").strip().lower()


def slugify(value):
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or uuid.uuid4().hex[:10]


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row else None


def json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def json_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def normalize_tokens(value):
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9áéíóúñü]+", " ", value)
    stopwords = {
        "para", "con", "sin", "por", "los", "las", "del", "una", "uno",
        "the", "and", "for", "your", "producto", "product", "ver",
    }
    return {
        token
        for token in value.split()
        if len(token) >= 3 and token not in stopwords
    }


def amazon_url_allowed(url, product, metadata):
    url = str(url or "").strip()
    if not re.search(r"(^|//)(www\.)?amazon\.", url, re.I):
        return True
    lowered = url.lower()
    if "/s?" in lowered or "/s/" in lowered or "/gp/search" in lowered:
        return False
    if not re.search(r"/(dp|gp/product)/[A-Z0-9]{10}", url, re.I):
        return False
    if (
        json_bool(metadata.get("amazon_verified") or metadata.get("marketplace_verified"))
        or str(metadata.get("image_source") or "").lower() == "amazon_verified"
    ):
        return True
    product_tokens = normalize_tokens(
        " ".join(
            item
            for item in [product.get("name"), product.get("category"), product.get("sku")]
            if item
        )
    )
    url_tokens = normalize_tokens(url.replace("-", " ").replace("+", " "))
    return bool(product_tokens and product_tokens.intersection(url_tokens))


def safe_source_link(link, product, metadata):
    if not isinstance(link, dict):
        return None
    url = str(link.get("url") or "").strip()
    if not url:
        return None
    if not amazon_url_allowed(url, product, metadata):
        return None
    return {
        "name": str(link.get("name") or link.get("label") or "Ver producto").strip(),
        "label": str(link.get("label") or link.get("name") or "Ver producto").strip(),
        "url": url,
        "type": str(link.get("type") or "").strip(),
    }


def image_publishable(metadata, has_uploaded_image=False):
    if has_uploaded_image:
        return True, 0.96
    source = str(metadata.get("image_source") or "").lower()
    score = float(metadata.get("image_match_score") or 0)
    curated = source in {"oye_bonita_assets", "platform_upload", "local_verified", "official"}
    verified = json_bool(metadata.get("image_verified"))
    if curated and verified:
        return True, max(score, 0.96)
    if verified and score >= 0.82:
        return True, score
    return False, score


def init_platform_db():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _USE_CLOUDINARY:
        import sys
        print(
            "[ADVERTENCIA] CLOUDINARY_URL no está configurado. "
            "Las imágenes se guardarán en disco local y se PERDERÁN si el servidor se reinicia "
            "(almacenamiento efímero en Render/Heroku). "
            "Configura CLOUDINARY_URL en las variables de entorno del servidor.",
            file=sys.stderr,
        )
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS platform_users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            account_type TEXT NOT NULL DEFAULT 'personal',
            full_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            avatar_url TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS platform_organizations (
            id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            org_type TEXT NOT NULL DEFAULT 'personal',
            tax_id TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            whatsapp TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES platform_users(id)
        );

        CREATE TABLE IF NOT EXISTS platform_memberships (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'owner',
            permissions_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            UNIQUE(user_id, organization_id),
            FOREIGN KEY(user_id) REFERENCES platform_users(id),
            FOREIGN KEY(organization_id) REFERENCES platform_organizations(id)
        );

        CREATE TABLE IF NOT EXISTS platform_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES platform_users(id)
        );

        CREATE TABLE IF NOT EXISTS platform_password_resets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES platform_users(id)
        );

        CREATE TABLE IF NOT EXISTS platform_products (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'USD',
            category TEXT NOT NULL DEFAULT '',
            stock INTEGER NOT NULL DEFAULT 0,
            priority INTEGER NOT NULL DEFAULT 3,
            status TEXT NOT NULL DEFAULT 'draft',
            product_url TEXT NOT NULL DEFAULT '',
            sku TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            published_at TEXT,
            UNIQUE(organization_id, slug),
            FOREIGN KEY(organization_id) REFERENCES platform_organizations(id),
            FOREIGN KEY(created_by_user_id) REFERENCES platform_users(id)
        );

        CREATE TABLE IF NOT EXISTS platform_product_media (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            media_type TEXT NOT NULL,
            url TEXT NOT NULL,
            storage_key TEXT NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES platform_products(id),
            FOREIGN KEY(organization_id) REFERENCES platform_organizations(id)
        );

        CREATE TABLE IF NOT EXISTS platform_promotions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            generated_by TEXT NOT NULL DEFAULT 'local_rules_v1',
            status TEXT NOT NULL DEFAULT 'draft',
            channel TEXT NOT NULL DEFAULT 'multi',
            title TEXT NOT NULL,
            promo_text TEXT NOT NULL,
            optimized_description TEXT NOT NULL,
            hashtags_json TEXT NOT NULL DEFAULT '[]',
            social_copy TEXT NOT NULL,
            whatsapp_message TEXT NOT NULL,
            campaign_ideas_json TEXT NOT NULL DEFAULT '[]',
            score REAL NOT NULL DEFAULT 0,
            schedule_for TEXT,
            generated_at TEXT NOT NULL,
            approved_at TEXT,
            published_at TEXT,
            FOREIGN KEY(organization_id) REFERENCES platform_organizations(id),
            FOREIGN KEY(product_id) REFERENCES platform_products(id)
        );

        CREATE TABLE IF NOT EXISTS platform_promotion_jobs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            frequency TEXT NOT NULL DEFAULT 'daily',
            run_at TEXT NOT NULL DEFAULT '09:00',
            rules_json TEXT NOT NULL DEFAULT '{}',
            auto_publish INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(organization_id) REFERENCES platform_organizations(id)
        );

        CREATE TABLE IF NOT EXISTS platform_product_metrics (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            metric_date TEXT NOT NULL,
            views INTEGER NOT NULL DEFAULT 0,
            clicks INTEGER NOT NULL DEFAULT 0,
            inquiries INTEGER NOT NULL DEFAULT 0,
            sales INTEGER NOT NULL DEFAULT 0,
            revenue REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(product_id, metric_date),
            FOREIGN KEY(product_id) REFERENCES platform_products(id)
        );

        CREATE TABLE IF NOT EXISTS platform_audit_logs (
            id TEXT PRIMARY KEY,
            actor_user_id TEXT,
            organization_id TEXT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_platform_products_org_status
            ON platform_products(organization_id, status);
        CREATE INDEX IF NOT EXISTS idx_platform_products_org_category
            ON platform_products(organization_id, category);
        CREATE INDEX IF NOT EXISTS idx_platform_media_product
            ON platform_product_media(product_id, sort_order);
        CREATE INDEX IF NOT EXISTS idx_platform_promotions_org_status
            ON platform_promotions(organization_id, status);
        CREATE INDEX IF NOT EXISTS idx_platform_sessions_token
            ON platform_sessions(token_hash);
        """
    )
    conn.commit()
    conn.close()


def audit(conn, actor_user_id, organization_id, entity_type, entity_id, action, payload=None):
    conn.execute(
        """
        INSERT INTO platform_audit_logs
        (id, actor_user_id, organization_id, entity_type, entity_id, action, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            make_id("aud"),
            actor_user_id,
            organization_id,
            entity_type,
            entity_id,
            action,
            json.dumps(payload or {}, ensure_ascii=False),
            now_iso(),
        ),
    )


def issue_session(conn, user_id):
    token = secrets.token_urlsafe(36)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)).replace(microsecond=0)
    conn.execute(
        """
        INSERT INTO platform_sessions
        (id, user_id, token_hash, expires_at, created_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (make_id("ses"), user_id, token_hash(token), expires_at.isoformat(), now_iso(), now_iso()),
    )
    return token, expires_at.isoformat()


def current_auth():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None

    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT s.id AS session_id, s.expires_at, u.*
            FROM platform_sessions s
            JOIN platform_users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND u.status = 'active'
            """,
            (token_hash(token),),
        ).fetchone()
        if not row:
            return None
        expires_at = parse_dt(row["expires_at"])
        if not expires_at or expires_at < datetime.now(timezone.utc):
            return None
        conn.execute(
            "UPDATE platform_sessions SET last_seen_at = ? WHERE id = ?",
            (now_iso(), row["session_id"]),
        )
        conn.commit()
        return {k: row[k] for k in row.keys() if k not in {"password_hash"}}
    finally:
        conn.close()


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_auth()
        if not user:
            return jsonify({"error": "Sesion requerida."}), 401
        return fn(user, *args, **kwargs)

    return wrapper


def get_memberships(conn, user_id):
    rows = conn.execute(
        """
        SELECT m.*, o.name AS organization_name, o.slug AS organization_slug,
               o.org_type, o.status AS organization_status, o.description,
               o.website, o.whatsapp, o.tax_id
        FROM platform_memberships m
        JOIN platform_organizations o ON o.id = m.organization_id
        WHERE m.user_id = ? AND m.status = 'active' AND o.status = 'active'
        ORDER BY o.created_at ASC
        """,
        (user_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def resolve_org(conn, user, requested_id=None):
    memberships = get_memberships(conn, user["id"])
    if not memberships:
        return None, None
    requested_id = requested_id or request.headers.get("X-Organization-Id")
    if requested_id:
        for membership in memberships:
            if membership["organization_id"] == requested_id:
                return requested_id, membership
        return None, None
    membership = memberships[0]
    return membership["organization_id"], membership


def require_role(membership, roles):
    return membership and membership.get("role") in roles


def clean_product(row, media=None):
    data = row_to_dict(row)
    if not data:
        return None
    data["metadata"] = json_loads(data.pop("metadata_json", "{}"), {})
    data["media"] = media or []
    return data


def product_media(conn, product_id):
    rows = conn.execute(
        """
        SELECT id, product_id, organization_id, media_type, url, storage_key,
               filename, mime_type, size_bytes, sort_order, created_at
        FROM platform_product_media
        WHERE product_id = ?
        ORDER BY sort_order ASC, created_at ASC
        """,
        (product_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def public_media_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if re.match(r"^https?://", url, re.I):
        return url
    return urljoin(request.host_url, url.lstrip("/"))


def public_product_payload(product_row, media_rows, organization_row):
    product = row_to_dict(product_row)
    media = [row_to_dict(row) if not isinstance(row, dict) else row for row in media_rows]
    organization = row_to_dict(organization_row) if organization_row else {}
    image = next((item for item in media if item.get("media_type") == "image"), None)
    video = next((item for item in media if item.get("media_type") == "video"), None)
    metadata = json_loads(product.get("metadata_json"), {})
    specs = metadata.get("technical_sheet") or metadata.get("ficha_tecnica") or []
    if isinstance(specs, dict):
        specs = [{"etiqueta": key, "valor": value} for key, value in specs.items()]
    if not isinstance(specs, list):
        specs = []
    base_specs = [
        {"etiqueta": "Categoria", "valor": product.get("category") or "Sin categoria"},
        {"etiqueta": "SKU", "valor": product.get("sku") or product.get("slug")},
        {"etiqueta": "Stock", "valor": product.get("stock")},
        {"etiqueta": "Prioridad comercial", "valor": product.get("priority")},
        {"etiqueta": "Empresa", "valor": organization.get("name") or "Perfil"},
    ]
    technical_sheet = base_specs + [
        {"etiqueta": str(item.get("etiqueta") or item.get("label") or item.get("name") or "Dato"), "valor": item.get("valor") or item.get("value") or ""}
        for item in specs
        if isinstance(item, dict)
    ]
    media_payload = [
        {
            "id": item.get("id"),
            "media_type": item.get("media_type"),
            "url": public_media_url(item.get("url")),
            "filename": item.get("filename"),
            "mime_type": item.get("mime_type"),
            "sort_order": item.get("sort_order"),
        }
        for item in media
    ]
    description = product.get("description") or f"{product.get('name')} disponible en {organization.get('name', 'la plataforma')}."
    metadata_image_raw = (
        metadata.get("image")
        or metadata.get("imagen")
        or metadata.get("imagen_ref")
        or ""
    )
    uploaded_image_url = public_media_url(image.get("url")) if image else ""
    metadata_image_ok, metadata_image_score = image_publishable(metadata, False)
    public_image = uploaded_image_url or (public_media_url(metadata_image_raw) if metadata_image_raw and metadata_image_ok else "")
    public_image_source = "platform_upload" if image else str(metadata.get("image_source") or "")
    public_image_score = 0.96 if image else metadata_image_score
    product_url_public = product.get("product_url") if amazon_url_allowed(product.get("product_url"), product, metadata) else ""
    source_links = []
    raw_source_links = metadata.get("source_links") if isinstance(metadata.get("source_links"), list) else []
    for link in raw_source_links:
        clean_link = safe_source_link(link, product, metadata)
        if clean_link:
            source_links.append(clean_link)
    if product_url_public:
        label = "Ver en Amazon" if "amazon." in product_url_public.lower() else "Ver producto"
        source_links.insert(0, {"name": label, "label": label, "url": product_url_public, "type": "marketplace" if "amazon." in product_url_public.lower() else ""})
    show_in_banner = json_bool(metadata.get("mostrar_en_banner", metadata.get("show_in_banner")))
    banner_image_raw = (
        metadata.get("banner_image")
        or metadata.get("imagen")
        or metadata.get("image")
        or ""
    )
    banner_image = (
        public_media_url(banner_image_raw)
        if banner_image_raw and (metadata_image_ok or not re.match(r"^https?://", str(banner_image_raw), re.I))
        else public_image
    )
    banner_title = metadata.get("banner_title") or metadata.get("title") or product.get("name")
    banner_description = (
        metadata.get("banner_description")
        or metadata.get("descripcion_corta")
        or metadata.get("short_desc")
        or description[:180]
    )
    banner_link = metadata.get("banner_link") or metadata.get("button_link") or product_url_public or ""
    banner_button_text = metadata.get("banner_button_text") or metadata.get("button_text") or metadata.get("cta") or "Ver producto"
    banner_category = metadata.get("banner_category") or product.get("category") or ""
    return {
        "id": product.get("id"),
        "organization_id": product.get("organization_id"),
        "organization_name": organization.get("name") or "",
        "name": product.get("name"),
        "brand": organization.get("name") or "",
        "category": product.get("category"),
        "short_desc": description[:180],
        "description": description,
        "problem": metadata.get("problem") or "Necesidad comercial detectada",
        "target": metadata.get("target") or "Clientes interesados en este producto",
        "specs": ", ".join(f"{item['etiqueta']}: {item['valor']}" for item in technical_sheet if item.get("valor") not in [None, ""]),
        "especificaciones_dinamicas": technical_sheet,
        "price_base": float(product.get("price") or 0),
        "price_sale": float(product.get("price") or 0),
        "currency": product.get("currency") or "USD",
        "stock": int(product.get("stock") or 0),
        "sku": product.get("sku") or "",
        "status": product.get("status"),
        "priority": int(product.get("priority") or 3),
        "product_url": product_url_public or "",
        "cta": "Ver ficha",
        "reason": metadata.get("reason") or f"Producto publicado por {organization.get('name', 'la empresa')} con ficha comercial disponible.",
        "hook": metadata.get("hook") or "Consulta disponibilidad, ficha tecnica y opciones de compra.",
        "image": public_image,
        "video": public_media_url(video.get("url")) if video else "",
        "media": media_payload,
        "image_verified": bool(public_image),
        "image_match_score": public_image_score if public_image else 0,
        "image_source": public_image_source,
        "source_links": source_links,
        "mostrar_en_banner": show_in_banner,
        "show_in_banner": show_in_banner,
        "banner_title": banner_title,
        "banner_description": banner_description,
        "banner_image": banner_image,
        "banner_link": banner_link,
        "banner_button_text": banner_button_text,
        "banner_category": banner_category,
        "banner": {
            "show": show_in_banner,
            "title": banner_title,
            "description": banner_description,
            "image": banner_image,
            "link": banner_link,
            "button_text": banner_button_text,
            "category": banner_category,
        },
        "search_query": " ".join(
            item for item in [product.get("name"), product.get("category"), organization.get("name"), product.get("sku")] if item
        ),
        "updated_at": product.get("updated_at"),
        "published_at": product.get("published_at"),
    }


def get_product_for_user(conn, user, product_id):
    row = conn.execute("SELECT * FROM platform_products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        return None, None
    _org_id, membership = resolve_org(conn, user, row["organization_id"])
    if not membership:
        return None, None
    return row, membership


def promotion_payload(row):
    data = row_to_dict(row)
    if not data:
        return None
    data["hashtags"] = json_loads(data.pop("hashtags_json", "[]"), [])
    data["campaign_ideas"] = json_loads(data.pop("campaign_ideas_json", "[]"), [])
    return data


def build_promotion(product, organization):
    name = product["name"]
    category = product["category"] or "producto"
    stock = int(product["stock"] or 0)
    priority = int(product["priority"] or 3)
    price = float(product["price"] or 0)
    currency = product["currency"] or "USD"
    description = product["description"] or f"{name} disponible en {organization['name']}."

    urgency = "stock limitado" if stock <= 5 else "disponible para entrega"
    price_line = f"{currency} {price:,.2f}" if price > 0 else "precio a consultar"
    title = f"{name}: oferta destacada para {category}"
    promo_text = (
        f"{name} esta {urgency}. Ideal para quienes buscan {category} con informacion clara, "
        f"atencion directa y compra segura. {price_line}."
    )
    optimized_description = (
        f"{description} Incluye disponibilidad, categoria {category}, prioridad comercial {priority} "
        "y enlace directo para cerrar la compra con menor friccion."
    )
    tags = [
        f"#{slugify(category).replace('-', '')}",
        f"#{slugify(organization['name']).replace('-', '')}",
        "#promocion",
        "#productos",
        "#ofertas",
    ]
    social_copy = (
        f"Hoy destacamos {name}. {urgency.capitalize()}, {price_line}. "
        "Consulta detalles y reserva antes de que cambie la disponibilidad."
    )
    whatsapp = (
        f"Hola, vi {name} en {organization['name']} y quiero mas informacion. "
        f"Me interesa precio, stock y forma de entrega. Codigo: {product['sku'] or product['id']}"
    )
    campaign_ideas = [
        f"Historia corta mostrando problema, solucion y precio de {name}.",
        f"Publicacion comparativa para explicar por que elegir {name} en {category}.",
        "Mensaje de recompra o referidos para clientes anteriores de la empresa.",
    ]
    score = min(100, 45 + (5 - min(priority, 5)) * 8 + (15 if stock > 0 else 0))
    return {
        "title": title,
        "promo_text": promo_text,
        "optimized_description": optimized_description,
        "hashtags": tags,
        "social_copy": social_copy,
        "whatsapp_message": whatsapp,
        "campaign_ideas": campaign_ideas,
        "score": score,
    }


@platform_bp.route("/auth/register", methods=["POST"])
def register():
    init_platform_db()
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    password = str(data.get("password") or "")
    full_name = str(data.get("full_name") or "").strip()
    account_type = str(data.get("account_type") or "personal").strip().lower()
    organization_name = str(data.get("organization_name") or full_name or email.split("@")[0]).strip()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Correo invalido."}), 400
    if len(password) < 8:
        return jsonify({"error": "La contrasena debe tener minimo 8 caracteres."}), 400
    if account_type not in {"personal", "company", "small_business", "admin"}:
        return jsonify({"error": "Tipo de cuenta invalido."}), 400

    conn = get_db()
    try:
        user_count = conn.execute("SELECT COUNT(*) AS total FROM platform_users").fetchone()["total"]
        if account_type == "admin" and user_count > 0:
            return jsonify({"error": "El rol administrador solo puede crearse como primer usuario."}), 403

        user_id = make_id("usr")
        org_id = make_id("org")
        timestamp = now_iso()
        org_slug = slugify(organization_name)
        while conn.execute("SELECT 1 FROM platform_organizations WHERE slug = ?", (org_slug,)).fetchone():
            org_slug = f"{slugify(organization_name)}-{secrets.token_hex(3)}"

        conn.execute(
            """
            INSERT INTO platform_users
            (id, email, password_hash, account_type, full_name, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                user_id,
                email,
                generate_password_hash(password),
                account_type,
                full_name or organization_name,
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT INTO platform_organizations
            (id, owner_user_id, name, slug, org_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                org_id,
                user_id,
                organization_name,
                org_slug,
                "company" if account_type in {"company", "small_business"} else "personal",
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT INTO platform_memberships
            (id, user_id, organization_id, role, permissions_json, status, created_at)
            VALUES (?, ?, ?, 'owner', ?, 'active', ?)
            """,
            (
                make_id("mem"),
                user_id,
                org_id,
                json.dumps({"products": "manage", "promotions": "manage"}, ensure_ascii=False),
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT INTO platform_promotion_jobs
            (id, organization_id, frequency, run_at, rules_json, auto_publish, status, created_at, updated_at)
            VALUES (?, ?, 'daily', '09:00', ?, 0, 'active', ?, ?)
            """,
            (
                make_id("job"),
                org_id,
                json.dumps({"stock_weight": True, "priority_weight": True, "category_rotation": True}, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        token, expires_at = issue_session(conn, user_id)
        audit(conn, user_id, org_id, "organization", org_id, "register")
        conn.commit()
        return jsonify(
            {
                "ok": True,
                "token": token,
                "expires_at": expires_at,
                "user": {"id": user_id, "email": email, "full_name": full_name or organization_name, "account_type": account_type},
                "organization": {"id": org_id, "name": organization_name, "slug": org_slug},
            }
        )
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "El correo ya esta registrado."}), 409
    finally:
        conn.close()


@platform_bp.route("/auth/login", methods=["POST"])
def login():
    init_platform_db()
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    password = str(data.get("password") or "")
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM platform_users WHERE email = ?", (email,)).fetchone()
        if not row or row["status"] != "active" or not check_password_hash(row["password_hash"], password):
            return jsonify({"error": "Correo o contrasena incorrectos."}), 401
        token, expires_at = issue_session(conn, row["id"])
        conn.commit()
        return jsonify(
            {
                "ok": True,
                "token": token,
                "expires_at": expires_at,
                "user": {
                    "id": row["id"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "account_type": row["account_type"],
                },
                "organizations": get_memberships(conn, row["id"]),
            }
        )
    finally:
        conn.close()


@platform_bp.route("/auth/request-password-reset", methods=["POST"])
def request_password_reset():
    init_platform_db()
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM platform_users WHERE email = ?", (email,)).fetchone()
        response = {"ok": True, "message": "Si el correo existe, se genero una solicitud de recuperacion."}
        if row:
            raw_token = secrets.token_urlsafe(32)
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=RESET_TTL_MINUTES)).replace(microsecond=0)
            conn.execute(
                """
                INSERT INTO platform_password_resets
                (id, user_id, token_hash, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (make_id("rst"), row["id"], token_hash(raw_token), expires_at.isoformat(), now_iso()),
            )
            conn.commit()
            if request.host.startswith(("127.0.0.1", "localhost")) or os.environ.get("PLATFORM_DEV_RESET_TOKEN") == "1":
                response["dev_reset_token"] = raw_token
        return jsonify(response)
    finally:
        conn.close()


@platform_bp.route("/auth/reset-password", methods=["POST"])
def reset_password():
    init_platform_db()
    data = request.get_json(silent=True) or {}
    raw_token = str(data.get("token") or "")
    new_password = str(data.get("new_password") or "")
    if len(new_password) < 8:
        return jsonify({"error": "La nueva contrasena debe tener minimo 8 caracteres."}), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM platform_password_resets WHERE token_hash = ? AND used_at IS NULL",
            (token_hash(raw_token),),
        ).fetchone()
        if not row:
            return jsonify({"error": "Token invalido."}), 400
        expires_at = parse_dt(row["expires_at"])
        if not expires_at or expires_at < datetime.now(timezone.utc):
            return jsonify({"error": "Token expirado."}), 400
        conn.execute(
            "UPDATE platform_users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (generate_password_hash(new_password), now_iso(), row["user_id"]),
        )
        conn.execute("UPDATE platform_password_resets SET used_at = ? WHERE id = ?", (now_iso(), row["id"]))
        conn.execute("DELETE FROM platform_sessions WHERE user_id = ?", (row["user_id"],))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@platform_bp.route("/admin/storage-status", methods=["GET"])
@require_auth
def storage_status(user):
    """Diagnóstico rápido: muestra si Cloudinary está activo y cuántos archivos quedan en disco local."""
    _org_id, membership = None, None
    conn = get_db()
    try:
        _org_id, membership = resolve_org(conn, user, request.args.get("organization_id"))
        if not require_role(membership, MANAGE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        local_count = conn.execute(
            "SELECT COUNT(*) AS n FROM platform_product_media WHERE storage_key NOT LIKE 'cloudinary:%'"
        ).fetchone()["n"]
        cloud_count = conn.execute(
            "SELECT COUNT(*) AS n FROM platform_product_media WHERE storage_key LIKE 'cloudinary:%'"
        ).fetchone()["n"]
        cld_info = {}
        if _USE_CLOUDINARY:
            try:
                cfg = cloudinary.config()
                cld_info = {"cloud_name": cfg.cloud_name, "configured": True}
            except Exception:
                cld_info = {"configured": True}
        return jsonify({
            "cloudinary_active": _USE_CLOUDINARY,
            "cloudinary": cld_info,
            "media_in_cloudinary": cloud_count,
            "media_in_local_disk": local_count,
            "db_path": str(DB_PATH),
            "upload_dir": str(UPLOAD_DIR),
        })
    finally:
        conn.close()


@platform_bp.route("/me", methods=["GET"])
@require_auth
def me(user):
    conn = get_db()
    try:
        return jsonify({"user": user, "organizations": get_memberships(conn, user["id"])})
    finally:
        conn.close()


@platform_bp.route("/profile", methods=["PUT"])
@require_auth
def update_profile(user):
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name") or user.get("full_name") or "").strip()
    phone = str(data.get("phone") or "").strip()
    avatar_url = str(data.get("avatar_url") or "").strip()
    conn = get_db()
    try:
        conn.execute(
            "UPDATE platform_users SET full_name = ?, phone = ?, avatar_url = ?, updated_at = ? WHERE id = ?",
            (full_name, phone, avatar_url, now_iso(), user["id"]),
        )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@platform_bp.route("/organizations/<organization_id>", methods=["PUT"])
@require_auth
def update_organization(user, organization_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        _org_id, membership = resolve_org(conn, user, organization_id)
        if not require_role(membership, MANAGE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        conn.execute(
            """
            UPDATE platform_organizations
            SET name = ?, tax_id = ?, description = ?, website = ?, whatsapp = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(data.get("name") or "").strip(),
                str(data.get("tax_id") or "").strip(),
                str(data.get("description") or "").strip(),
                str(data.get("website") or "").strip(),
                str(data.get("whatsapp") or "").strip(),
                now_iso(),
                organization_id,
            ),
        )
        audit(conn, user["id"], organization_id, "organization", organization_id, "update", data)
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@platform_bp.route("/dashboard", methods=["GET"])
@require_auth
def dashboard(user):
    organization_id = request.args.get("organization_id")
    conn = get_db()
    try:
        org_id, membership = resolve_org(conn, user, organization_id)
        if not membership:
            return jsonify({"error": "Empresa no encontrada."}), 404
        summary = conn.execute(
            """
            SELECT
              COUNT(*) AS total_products,
              SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) AS published_products,
              SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) AS draft_products,
              SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) AS archived_products,
              SUM(CASE WHEN stock <= 5 AND status != 'archived' THEN 1 ELSE 0 END) AS low_stock_products,
              COALESCE(SUM(stock), 0) AS total_stock
            FROM platform_products
            WHERE organization_id = ?
            """,
            (org_id,),
        ).fetchone()
        promo = conn.execute(
            """
            SELECT
              COUNT(*) AS total_promotions,
              SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) AS draft_promotions,
              SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved_promotions,
              SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) AS published_promotions
            FROM platform_promotions
            WHERE organization_id = ?
            """,
            (org_id,),
        ).fetchone()
        recent_products = conn.execute(
            """
            SELECT * FROM platform_products
            WHERE organization_id = ?
            ORDER BY updated_at DESC
            LIMIT 6
            """,
            (org_id,),
        ).fetchall()
        recent_promotions = conn.execute(
            """
            SELECT pr.*, p.name AS product_name
            FROM platform_promotions pr
            JOIN platform_products p ON p.id = pr.product_id
            WHERE pr.organization_id = ?
            ORDER BY pr.generated_at DESC
            LIMIT 6
            """,
            (org_id,),
        ).fetchall()
        return jsonify(
            {
                "organization_id": org_id,
                "membership": membership,
                "summary": row_to_dict(summary),
                "promotions": row_to_dict(promo),
                "recent_products": [clean_product(row) for row in recent_products],
                "recent_promotions": [promotion_payload(row) for row in recent_promotions],
            }
        )
    finally:
        conn.close()


@platform_bp.route("/products", methods=["GET"])
@require_auth
def list_products(user):
    organization_id = request.args.get("organization_id")
    q = str(request.args.get("q") or "").strip().lower()
    status = str(request.args.get("status") or "").strip()
    category = str(request.args.get("category") or "").strip()
    conn = get_db()
    try:
        org_id, membership = resolve_org(conn, user, organization_id)
        if not membership:
            return jsonify({"error": "Empresa no encontrada."}), 404

        clauses = ["organization_id = ?"]
        params = [org_id]
        if q:
            clauses.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(sku) LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        if status:
            clauses.append("status = ?")
            params.append(status)
        if category:
            clauses.append("category = ?")
            params.append(category)

        rows = conn.execute(
            f"""
            SELECT * FROM platform_products
            WHERE {' AND '.join(clauses)}
            ORDER BY priority ASC,
              CASE WHEN sku GLOB '[0-9]*' AND sku != '' THEN 0 ELSE 1 END ASC,
              CAST(sku AS INTEGER) ASC,
              sku ASC,
              updated_at DESC
            LIMIT 200
            """,
            params,
        ).fetchall()
        products = [clean_product(row, product_media(conn, row["id"])) for row in rows]
        categories = sorted({p["category"] for p in products if p.get("category")})
        return jsonify({"products": products, "categories": categories})
    finally:
        conn.close()


@platform_bp.route("/public-products", methods=["GET"])
def public_products():
    init_platform_db()
    organization_id = request.args.get("organization_id")
    q = str(request.args.get("q") or "").strip().lower()
    limit = max(1, min(100, int(request.args.get("limit") or 48)))
    conn = get_db()
    try:
        clauses = ["p.status = 'published'", "o.status = 'active'"]
        params = []
        if organization_id:
            clauses.append("p.organization_id = ?")
            params.append(organization_id)
        if q:
            clauses.append("(LOWER(p.name) LIKE ? OR LOWER(p.description) LIKE ? OR LOWER(p.category) LIKE ? OR LOWER(p.sku) LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        rows = conn.execute(
            f"""
            SELECT p.*, o.name AS organization_name
            FROM platform_products p
            JOIN platform_organizations o ON o.id = p.organization_id
            WHERE {' AND '.join(clauses)}
            ORDER BY p.priority ASC,
              CASE WHEN p.sku GLOB '[0-9]*' AND p.sku != '' THEN 0 ELSE 1 END ASC,
              CAST(p.sku AS INTEGER) ASC,
              p.sku ASC,
              p.updated_at DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
        products = []
        for row in rows:
            organization = conn.execute(
                "SELECT * FROM platform_organizations WHERE id = ?",
                (row["organization_id"],),
            ).fetchone()
            products.append(public_product_payload(row, product_media(conn, row["id"]), organization))
        return jsonify({"ok": True, "total": len(products), "products": products})
    finally:
        conn.close()


@platform_bp.route("/products", methods=["POST"])
@require_auth
def create_product(user):
    data = request.get_json(silent=True) or {}
    organization_id = data.get("organization_id")
    conn = get_db()
    try:
        org_id, membership = resolve_org(conn, user, organization_id)
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        name = str(data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "El nombre del producto es obligatorio."}), 400
        product_id = make_id("prd")
        timestamp = now_iso()
        slug = slugify(name)
        while conn.execute(
            "SELECT 1 FROM platform_products WHERE organization_id = ? AND slug = ?",
            (org_id, slug),
        ).fetchone():
            slug = f"{slugify(name)}-{secrets.token_hex(2)}"
        status = str(data.get("status") or "draft").strip()
        published_at = timestamp if status == "published" else None
        conn.execute(
            """
            INSERT INTO platform_products
            (id, organization_id, created_by_user_id, name, slug, description, price, currency,
             category, stock, priority, status, product_url, sku, metadata_json, created_at,
             updated_at, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                org_id,
                user["id"],
                name,
                slug,
                str(data.get("description") or "").strip(),
                float(data.get("price") or 0),
                str(data.get("currency") or "USD").strip().upper()[:6],
                str(data.get("category") or "").strip(),
                int(data.get("stock") or 0),
                max(1, min(5, int(data.get("priority") or 3))),
                status if status in {"draft", "published", "archived"} else "draft",
                str(data.get("product_url") or "").strip(),
                str(data.get("sku") or "").strip(),
                json.dumps(data.get("metadata") or {}, ensure_ascii=False),
                timestamp,
                timestamp,
                published_at,
            ),
        )
        audit(conn, user["id"], org_id, "product", product_id, "create", data)
        conn.commit()
        row = conn.execute("SELECT * FROM platform_products WHERE id = ?", (product_id,)).fetchone()
        return jsonify({"ok": True, "product": clean_product(row, [])}), 201
    finally:
        conn.close()


@platform_bp.route("/products/<product_id>", methods=["GET"])
@require_auth
def get_product(user, product_id):
    conn = get_db()
    try:
        row, _membership = get_product_for_user(conn, user, product_id)
        if not row:
            return jsonify({"error": "Producto no encontrado."}), 404
        return jsonify({"product": clean_product(row, product_media(conn, product_id))})
    finally:
        conn.close()


@platform_bp.route("/products/<product_id>", methods=["PUT"])
@require_auth
def update_product(user, product_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        row, membership = get_product_for_user(conn, user, product_id)
        if not row:
            return jsonify({"error": "Producto no encontrado."}), 404
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        name = str(data.get("name", row["name"]) or "").strip()
        if not name:
            return jsonify({"error": "El nombre del producto es obligatorio."}), 400
        status = str(data.get("status", row["status"]) or "draft").strip()
        status = status if status in {"draft", "published", "archived"} else row["status"]
        published_at = row["published_at"] or (now_iso() if status == "published" else None)
        conn.execute(
            """
            UPDATE platform_products
            SET name = ?, description = ?, price = ?, currency = ?, category = ?, stock = ?,
                priority = ?, status = ?, product_url = ?, sku = ?, metadata_json = ?,
                updated_at = ?, published_at = ?
            WHERE id = ?
            """,
            (
                name,
                str(data.get("description", row["description"]) or "").strip(),
                float(data.get("price", row["price"]) or 0),
                str(data.get("currency", row["currency"]) or "USD").strip().upper()[:6],
                str(data.get("category", row["category"]) or "").strip(),
                int(data.get("stock", row["stock"]) or 0),
                max(1, min(5, int(data.get("priority", row["priority"]) or 3))),
                status,
                str(data.get("product_url", row["product_url"]) or "").strip(),
                str(data.get("sku", row["sku"]) or "").strip(),
                json.dumps(data.get("metadata") or json_loads(row["metadata_json"], {}), ensure_ascii=False),
                now_iso(),
                published_at,
                product_id,
            ),
        )
        audit(conn, user["id"], row["organization_id"], "product", product_id, "update", data)
        conn.commit()
        updated = conn.execute("SELECT * FROM platform_products WHERE id = ?", (product_id,)).fetchone()
        return jsonify({"ok": True, "product": clean_product(updated, product_media(conn, product_id))})
    finally:
        conn.close()


@platform_bp.route("/products/<product_id>", methods=["DELETE"])
@require_auth
def archive_product(user, product_id):
    conn = get_db()
    try:
        row, membership = get_product_for_user(conn, user, product_id)
        if not row:
            return jsonify({"error": "Producto no encontrado."}), 404
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        conn.execute(
            "UPDATE platform_products SET status = 'archived', updated_at = ? WHERE id = ?",
            (now_iso(), product_id),
        )
        audit(conn, user["id"], row["organization_id"], "product", product_id, "archive")
        conn.commit()
        return jsonify({"ok": True, "status": "archived"})
    finally:
        conn.close()


@platform_bp.route("/products/<product_id>/media", methods=["POST"])
@require_auth
def upload_product_media(user, product_id):
    conn = get_db()
    try:
        row, membership = get_product_for_user(conn, user, product_id)
        if not row:
            return jsonify({"error": "Producto no encontrado."}), 404
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        files = request.files.getlist("files") or request.files.getlist("media")
        if not files:
            file = request.files.get("file")
            files = [file] if file else []
        saved = []
        base_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM platform_product_media WHERE product_id = ?",
            (product_id,),
        ).fetchone()["max_order"]
        for index, file in enumerate(files, start=1):
            raw = file.read()
            size = len(raw)
            if size <= 0:
                continue
            mime_type = file.mimetype or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
            if mime_type in IMAGE_MIMES:
                media_type = "image"
            elif mime_type in VIDEO_MIMES:
                media_type = "video"
            else:
                return jsonify({"error": f"Tipo de archivo no permitido: {mime_type}"}), 400
            original = secure_filename(file.filename or f"media-{index}")
            ext = Path(original).suffix or mimetypes.guess_extension(mime_type) or ".bin"
            storage_name = f"{product_id}-{uuid.uuid4().hex}{ext}"
            media_id = make_id("med")
            cld_resource_type = "video" if media_type == "video" else "image"
            if _USE_CLOUDINARY:
                cld_public_id = f"amatoty/productos/{storage_name}"
                try:
                    public_url = _cloudinary_upload(raw, cld_public_id, cld_resource_type)
                except RuntimeError as cld_err:
                    # Fallback: guardar localmente si Cloudinary falla
                    try:
                        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                        target = UPLOAD_DIR / storage_name
                        target.write_bytes(raw)
                        public_url = f"{PUBLIC_UPLOAD_PREFIX}/{storage_name}"
                        cld_public_id = None  # no hay que borrarlo de Cloudinary
                    except Exception:
                        return jsonify({"error": f"No se pudo guardar el archivo. {cld_err}"}), 500
                # storage_key guarda el public_id para poder borrarlo después
                if cld_public_id:
                    storage_key_val = f"cloudinary:{cld_resource_type}:{cld_public_id}"
                else:
                    storage_key_val = str((UPLOAD_DIR / storage_name).relative_to(BASE_DIR))
                # también guardamos en disco local como caché (ignorar si falla)
                try:
                    target = UPLOAD_DIR / storage_name
                    target.write_bytes(raw)
                except Exception:
                    pass
            else:
                UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                target = UPLOAD_DIR / storage_name
                target.write_bytes(raw)
                public_url = f"{PUBLIC_UPLOAD_PREFIX}/{storage_name}"
                storage_key_val = str(target.relative_to(BASE_DIR))
            conn.execute(
                """
                INSERT INTO platform_product_media
                (id, product_id, organization_id, media_type, url, storage_key, filename,
                 mime_type, size_bytes, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    product_id,
                    row["organization_id"],
                    media_type,
                    public_url,
                    storage_key_val,
                    original,
                    mime_type,
                    size,
                    base_order + index,
                    now_iso(),
                ),
            )
            saved.append(
                {
                    "id": media_id,
                    "media_type": media_type,
                    "url": public_url,
                    "filename": original,
                    "mime_type": mime_type,
                    "size_bytes": size,
                }
            )
        audit(conn, user["id"], row["organization_id"], "product", product_id, "upload_media", {"count": len(saved)})
        conn.commit()
        return jsonify({"ok": True, "media": saved})
    except Exception as exc:
        return jsonify({"error": f"Error al subir archivo: {exc}"}), 500
    finally:
        conn.close()


@platform_bp.route("/media/<media_id>", methods=["DELETE"])
@require_auth
def delete_media(user, media_id):
    conn = get_db()
    try:
        media = conn.execute("SELECT * FROM platform_product_media WHERE id = ?", (media_id,)).fetchone()
        if not media:
            return jsonify({"error": "Archivo no encontrado."}), 404
        _org_id, membership = resolve_org(conn, user, media["organization_id"])
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        storage_key = media["storage_key"] or ""
        if storage_key.startswith("cloudinary:"):
            # formato: "cloudinary:<resource_type>:<public_id>"
            parts = storage_key.split(":", 2)
            cld_resource_type = parts[1] if len(parts) > 1 else "image"
            cld_public_id = parts[2] if len(parts) > 2 else ""
            if cld_public_id:
                _cloudinary_delete(cld_public_id, cld_resource_type)
        else:
            storage_path = BASE_DIR / storage_key
            if storage_path.is_file():
                storage_path.unlink(missing_ok=True)
        conn.execute("DELETE FROM platform_product_media WHERE id = ?", (media_id,))
        audit(conn, user["id"], media["organization_id"], "media", media_id, "delete")
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@platform_bp.route("/admin/migrate-media-to-cloudinary", methods=["POST"])
@require_auth
def migrate_media_to_cloudinary(user):
    """Sube a Cloudinary todas las imágenes/videos que están guardados en disco local.
    Solo accesible para roles owner/admin. Idempotente: si ya está en Cloudinary, lo omite."""
    conn = get_db()
    try:
        _org_id, membership = resolve_org(conn, user, request.json.get("organization_id") if request.is_json else None)
        if not require_role(membership, MANAGE_ROLES):
            return jsonify({"error": "Permiso insuficiente. Se requiere owner o admin."}), 403
        if not _USE_CLOUDINARY:
            return jsonify({"error": "Cloudinary no está configurado. Agrega CLOUDINARY_URL en las variables de entorno."}), 400

        rows = conn.execute(
            "SELECT id, media_type, url, storage_key, filename, mime_type FROM platform_product_media"
            " WHERE storage_key NOT LIKE 'cloudinary:%'"
        ).fetchall()

        migrated, skipped, errors = [], [], []
        for row in rows:
            media_id = row["id"]
            storage_key = row["storage_key"] or ""
            # Determinar ruta local del archivo
            if storage_key:
                local_path = BASE_DIR / storage_key
            else:
                # Intentar por URL legacy (ej: "Productos/archivo.jpg")
                url_part = (row["url"] or "").lstrip("/")
                local_path = BASE_DIR / url_part

            if not local_path.is_file():
                skipped.append({"id": media_id, "reason": f"Archivo no encontrado: {local_path}"})
                continue

            try:
                raw = local_path.read_bytes()
                cld_resource_type = "video" if row["media_type"] == "video" else "image"
                storage_name = local_path.name
                cld_public_id = f"amatoty/productos/{storage_name}"
                public_url = _cloudinary_upload(raw, cld_public_id, cld_resource_type)
                new_storage_key = f"cloudinary:{cld_resource_type}:{cld_public_id}"
                conn.execute(
                    "UPDATE platform_product_media SET url = ?, storage_key = ? WHERE id = ?",
                    (public_url, new_storage_key, media_id),
                )
                migrated.append({"id": media_id, "url": public_url})
            except Exception as exc:
                errors.append({"id": media_id, "error": str(exc)})

        conn.commit()
        return jsonify({
            "ok": True,
            "migrated": len(migrated),
            "skipped": len(skipped),
            "errors": len(errors),
            "detail_migrated": migrated,
            "detail_skipped": skipped,
            "detail_errors": errors,
        })
    finally:
        conn.close()


@platform_bp.route("/promotions", methods=["GET"])
@require_auth
def list_promotions(user):
    organization_id = request.args.get("organization_id")
    product_id = request.args.get("product_id")
    conn = get_db()
    try:
        org_id, membership = resolve_org(conn, user, organization_id)
        if not membership:
            return jsonify({"error": "Empresa no encontrada."}), 404
        clauses = ["pr.organization_id = ?"]
        params = [org_id]
        if product_id:
            clauses.append("pr.product_id = ?")
            params.append(product_id)
        rows = conn.execute(
            f"""
            SELECT pr.*, p.name AS product_name
            FROM platform_promotions pr
            JOIN platform_products p ON p.id = pr.product_id
            WHERE {' AND '.join(clauses)}
            ORDER BY pr.generated_at DESC
            LIMIT 100
            """,
            params,
        ).fetchall()
        return jsonify({"promotions": [promotion_payload(row) for row in rows]})
    finally:
        conn.close()


@platform_bp.route("/promotions/generate", methods=["POST"])
@require_auth
def generate_promotion(user):
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    conn = get_db()
    try:
        row, membership = get_product_for_user(conn, user, product_id)
        if not row:
            return jsonify({"error": "Producto no encontrado."}), 404
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        organization = conn.execute(
            "SELECT * FROM platform_organizations WHERE id = ?",
            (row["organization_id"],),
        ).fetchone()
        promo = build_promotion(row, organization)
        promo_id = make_id("prm")
        conn.execute(
            """
            INSERT INTO platform_promotions
            (id, organization_id, product_id, generated_by, status, channel, title,
             promo_text, optimized_description, hashtags_json, social_copy,
             whatsapp_message, campaign_ideas_json, score, schedule_for, generated_at)
            VALUES (?, ?, ?, 'local_rules_v1', 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                promo_id,
                row["organization_id"],
                product_id,
                str(data.get("channel") or "multi"),
                promo["title"],
                promo["promo_text"],
                promo["optimized_description"],
                json.dumps(promo["hashtags"], ensure_ascii=False),
                promo["social_copy"],
                promo["whatsapp_message"],
                json.dumps(promo["campaign_ideas"], ensure_ascii=False),
                promo["score"],
                data.get("schedule_for"),
                now_iso(),
            ),
        )
        audit(conn, user["id"], row["organization_id"], "promotion", promo_id, "generate", {"product_id": product_id})
        conn.commit()
        created = conn.execute(
            """
            SELECT pr.*, p.name AS product_name
            FROM platform_promotions pr
            JOIN platform_products p ON p.id = pr.product_id
            WHERE pr.id = ?
            """,
            (promo_id,),
        ).fetchone()
        return jsonify({"ok": True, "promotion": promotion_payload(created)})
    finally:
        conn.close()


@platform_bp.route("/promotions/<promotion_id>/approve", methods=["POST"])
@require_auth
def approve_promotion(user, promotion_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM platform_promotions WHERE id = ?", (promotion_id,)).fetchone()
        if not row:
            return jsonify({"error": "Promocion no encontrada."}), 404
        _org_id, membership = resolve_org(conn, user, row["organization_id"])
        if not require_role(membership, WRITE_ROLES):
            return jsonify({"error": "Permiso insuficiente."}), 403
        conn.execute(
            "UPDATE platform_promotions SET status = 'approved', approved_at = ? WHERE id = ?",
            (now_iso(), promotion_id),
        )
        audit(conn, user["id"], row["organization_id"], "promotion", promotion_id, "approve")
        conn.commit()
        return jsonify({"ok": True, "status": "approved"})
    finally:
        conn.close()


@platform_bp.route("/promotions/next-suggestions", methods=["GET"])
@require_auth
def next_promotion_suggestions(user):
    organization_id = request.args.get("organization_id")
    conn = get_db()
    try:
        org_id, membership = resolve_org(conn, user, organization_id)
        if not membership:
            return jsonify({"error": "Empresa no encontrada."}), 404
        rows = conn.execute(
            """
            SELECT p.*,
                   COUNT(pr.id) AS promotion_count,
                   MAX(pr.generated_at) AS last_promotion_at
            FROM platform_products p
            LEFT JOIN platform_promotions pr ON pr.product_id = p.id
            WHERE p.organization_id = ? AND p.status != 'archived' AND p.stock > 0
            GROUP BY p.id
            ORDER BY p.priority ASC, promotion_count ASC, p.stock DESC, p.updated_at DESC
            LIMIT 5
            """,
            (org_id,),
        ).fetchall()
        return jsonify({"suggestions": [clean_product(row, product_media(conn, row["id"])) for row in rows]})
    finally:
        conn.close()
