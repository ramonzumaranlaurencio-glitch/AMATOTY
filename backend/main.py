@app.get("/")
def home():
    return "AMATOTY backend activo", 200
from fastapi import FastAPI
from pydantic import BaseModel
import json
import datetime
import requests

app = FastAPI()

class Product(BaseModel):
    name: str
    brand: str = ""
    category: str
    problem: str
    target: str
    seo_title: str
    short_desc: str
    article: str
    hook: str
    cta: str
    reason: str
    decision: str
    image: str = ""
    specs: str = ""

@app.get("/trending-products")
def get_trending_products():
    with open("../docs/assets/trending_products.json", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.post("/update-product")
def update_product(product: Product):
    with open("../docs/assets/trending_products.json", encoding="utf-8") as f:
        data = json.load(f)
    data['products'].append(product.dict())
    with open("../docs/assets/trending_products.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "product": product}

@app.get("/google-trends/{keyword}")
def google_trends(keyword: str):
    # Placeholder: Integrar con pytrends o scraping real
    return {"keyword": keyword, "trend": "alta"}

@app.get("/health")
def health():
    return {"status": "ok", "date": str(datetime.date.today())}
