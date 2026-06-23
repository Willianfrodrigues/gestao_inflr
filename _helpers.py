import os, json, jwt, psycopg2
from google.cloud import bigquery
from functools import lru_cache

# ── CONFIG ────────────────────────────────────────────────────
JWT_SECRET   = os.environ.get('JWT_SECRET', 'inflr-gestao-2026')
DATABASE_URL = os.environ.get('DATABASE_URL', '')
GCP_PROJECT  = os.environ.get('GCP_PROJECT', 'looker-integrations-402615')

BQ_TABLE_3 = f"`{GCP_PROJECT}.tiktok_ads.conjunto mesclado 3`"
BQ_TABLE_1 = f"`{GCP_PROJECT}.tiktok_ads.Conjunto_mesclado`"

# ── NEON POSTGRESQL ───────────────────────────────────────────
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gestao_users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nome TEXT,
            role TEXT DEFAULT 'viewer',
            perms TEXT[] DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gestao_clients (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            emp TEXT,
            username TEXT,
            password TEXT,
            cor TEXT DEFAULT '#2DD9C0',
            logo TEXT,
            mets TEXT[] DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gestao_camps (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            client_id TEXT REFERENCES gestao_clients(id) ON DELETE CASCADE,
            kws TEXT[] DEFAULT '{}',
            ex TEXT[] DEFAULT '{}',
            ini DATE, fim DATE,
            clk TEXT DEFAULT 'clicks_link',
            plt TEXT[] DEFAULT '{}',
            cpm_cli NUMERIC DEFAULT 0,
            investimento NUMERIC DEFAULT 0,
            meta_imp BIGINT DEFAULT 0,
            org_ativo BOOLEAN DEFAULT FALSE,
            org_url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gestao_infl_corrections (
            id SERIAL PRIMARY KEY,
            camp_id TEXT REFERENCES gestao_camps(id) ON DELETE CASCADE,
            ad_name TEXT NOT NULL,
            ad_group TEXT,
            nome_correto TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(camp_id, ad_name)
        )""")
    # Admin padrão
    cur.execute("""
        INSERT INTO gestao_users (username, password, nome, role, perms)
        VALUES ('admin','inflr2026','inflr Admin','admin',
          ARRAY['gerencial','cliente-view','adm-clientes','adm-campanhas',
                'adm-admins','cs-painel','adm-influenciadores','financeiro'])
        ON CONFLICT (username) DO NOTHING""")
    conn.commit(); cur.close(); conn.close()

# ── BIGQUERY ──────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_bq():
    return bigquery.Client(project=GCP_PROJECT)

def bq_rows(query):
    rows = list(get_bq().query(query).result())
    result = []
    for r in rows:
        row = {}
        for k, v in r.items():
            row[k] = str(v) if hasattr(v, 'isoformat') else v
        result.append(row)
    return result

def build_camp_filter(kws, ex):
    if not kws:
        return '1=1'
    inc = ' OR '.join([f"UPPER(CAMPAIGN_NAME) LIKE '%{k.upper()}%'" for k in kws])
    parts = [f'({inc})']
    for e in (ex or []):
        parts.append(f"UPPER(CAMPAIGN_NAME) NOT LIKE '%{e.upper()}%'")
    return ' AND '.join(parts)

# ── JWT ───────────────────────────────────────────────────────
def make_token(payload):
    import time
    payload['exp'] = int(time.time()) + 86400 * 7
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

def get_token(headers):
    auth = headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        raise PermissionError('Token ausente.')
    try:
        return decode_token(auth[7:])
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError('Token expirado.')
    except Exception:
        raise PermissionError('Token inválido.')

# ── RESPOSTA ──────────────────────────────────────────────────
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Content-Type': 'application/json',
}

def ok(data, status=200):
    from http.server import BaseHTTPRequestHandler
    class R:
        def __init__(self):
            self.status_code = status
            self.headers = CORS
            self._data = json.dumps(data, default=str)
        def __call__(self, environ, start_response):
            start_response(f'{status} OK', list(self.headers.items()))
            return [self._data.encode()]
    return R()

def err(msg, status=400):
    return ok({'error': msg}, status)

def respond(handler, data=None, error=None, status=200):
    """Helper para responder em funções Vercel (http.server style)"""
    import json
    body = json.dumps(data or {'error': error}, default=str).encode()
    handler.send_response(status if not error else (400 if status==200 else status))
    for k, v in CORS.items():
        handler.send_header(k, v)
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
