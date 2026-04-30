from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)
DB_PATH = 'data/lca_pro_final.db'

def init_db():
    c = sqlite3.connect(DB_PATH)
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS tracking_events (id TEXT PRIMARY KEY, product_name TEXT, source TEXT, event_type TEXT, page_url TEXT, referrer TEXT, user_agent TEXT, created_at TEXT)""")
    c.commit(); c.close()

@app.route('/track', methods=['POST'])
def track():
    data = request.get_json(force=True) or {}
    c = sqlite3.connect(DB_PATH)
    cur = c.cursor()
    cur.execute("""INSERT INTO tracking_events (id, product_name, source, event_type, page_url, referrer, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (str(uuid.uuid4()), data.get('product_name',''), data.get('source',''), data.get('event_type',''), data.get('page_url',''), data.get('referrer',''), request.headers.get('User-Agent',''), datetime.now().isoformat()))
    c.commit(); c.close()
    return jsonify({'ok': True})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5055)
