import os, json, jwt, psycopg2
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account

def _env(key, default=None):
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val

GCP_PROJECT  = os.environ.get("GCP_PROJECT", "looker-integrations-402615")
BQ_TABLE_3   = f"`{GCP_PROJECT}.tiktok_ads.conjunto mesclado 3`"
BQ_TABLE_1   = f"`{GCP_PROJECT}.tiktok_ads.Conjunto_mesclado`"

# ── NEON ─────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(_env("NEON_DATABASE_URL"), sslmode="require")

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
    cur.execute("""
        INSERT INTO gestao_users (username, password, nome, role, perms)
        VALUES ('admin','inflr2026','inflr Admin','admin',
          ARRAY['gerencial','cliente-view','adm-clientes','adm-campanhas',
                'adm-admins','cs-painel','adm-influenciadores','financeiro'])
        ON CONFLICT (username) DO NOTHING""")
    conn.commit(); cur.close(); conn.close()

# ── BIGQUERY ──────────────────────────────────────────────────
def get_bq():
    sa_json = os.environ.get("BQ_SERVICE_ACCOUNT_JSON", "")
    if sa_json:
        info  = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(info)
        return bigquery.Client(credentials=creds, project=GCP_PROJECT)
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
JWT_SECRET = os.environ.get("JWT_SECRET", "inflr@2026#segredo!")

def make_token(payload):
    payload = dict(payload)
    payload['exp'] = datetime.utcnow() + timedelta(days=7)
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

def get_token_from_header(headers):
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise PermissionError("Token não encontrado.")
    try:
        return decode_token(auth[7:])
    except jwt.ExpiredSignatureError:
        raise
    except jwt.PyJWTError as e:
        raise PermissionError(f"Token inválido: {e}")

# ── RESPONSE HELPERS ──────────────────────────────────────────
def cors_headers():
    return {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Content-Type": "application/json"
    }

def json_response(data, status=200):
    return {
        "statusCode": status,
        "headers":    cors_headers(),
        "body":       json.dumps(data, default=str)
    }

def error_response(msg, status=400):
    return json_response({"error": msg}, status)
