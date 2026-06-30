import json, traceback
import jwt
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from _helpers import (get_db, get_bq, build_camp_filter, get_token_from_header,
                      json_response, error_response, cors_headers,
                      BQ_TABLE_3, BQ_TABLE_1)

def bq_rows(query):
    rows = list(get_bq().query(query).result())
    result = []
    for r in rows:
        row = {}
        for k, v in r.items():
            row[k] = str(v) if hasattr(v, 'isoformat') else v
        result.append(row)
    return result

# Mapeamento frontend → BigQuery
PLT_BQ_MAP = {
    'meta':    'facebook ads',
    'tiktok':  'tiktok ads',
    'dv360':   'google dv360',
}

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items(): self.send_header(k, v)
        self.end_headers()

    def _send(self, resp):
        self.send_response(resp["statusCode"])
        for k, v in resp["headers"].items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp["body"].encode())

    def do_GET(self):
        try:
            get_token_from_header(self.headers)
            parsed  = urlparse(self.path)
            params  = parse_qs(parsed.query)
            start   = params.get("start_date", [""])[0]
            end     = params.get("end_date",   [""])[0]
            type_   = params.get("type",       ["kpi"])[0]
            camp_id = params.get("camp_id",    [""])[0]
            plt     = params.get("platform",   [""])[0]

            if not start or not end:
                return self._send(error_response("start_date e end_date obrigatórios."))

            kws, ex = [], []
            if camp_id:
                conn = get_db(); cur = conn.cursor()
                cur.execute("SELECT kws, ex FROM gestao_camps WHERE id=%s", (camp_id,))
                row = cur.fetchone()
                cur.close(); conn.close()
                if row:
                    kws, ex = list(row[0] or []), list(row[1] or [])

            f = build_camp_filter(kws, ex)

            if plt:
                plt_val = PLT_BQ_MAP.get(plt.lower(), plt.lower())
                f = f + f" AND LOWER(TRIM(platform)) = '{plt_val}'"

            if type_ == "kpi":
                q = f"""
                SELECT
                    SUM(COALESCE(IMPRESSIONS,0))   AS impressions,
                    SUM(COALESCE(CLICKS,0))         AS clicks,
                    SUM(COALESCE(CLICKS_LINK,0))    AS clicks_link,
                    SUM(COALESCE(THRUPLAY,0))       AS thruplay,
                    SUM(COALESCE(VIEWS100,0))       AS views100,
                    SUM(COALESCE(total_comments,0)) AS comments,
                    SUM(COALESCE(total_reacoes,0))  AS reactions,
                    SUM(COALESCE(total_compartilhamento,0)) AS shares,
                    SUM(COALESCE(total_comments,0)+COALESCE(total_compartilhamento,0)+COALESCE(total_reacoes,0)+COALESCE(total_salvamentos,0)) AS engagement,
                    SAFE_DIVIDE(SUM(COALESCE(CLICKS_LINK,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS ctr,
                    SAFE_DIVIDE(SUM(COALESCE(THRUPLAY,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS vtr,
                    SAFE_DIVIDE(
                        SUM(COALESCE(total_comments,0)+COALESCE(total_compartilhamento,0)+COALESCE(total_reacoes,0)+COALESCE(total_salvamentos,0)),
                        NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0)
                    )*100 AS engagement_rate
                FROM {BQ_TABLE_3}
                WHERE date BETWEEN '{start}' AND '{end}' AND {f}
                """
                rows = bq_rows(q)
                return self._send(json_response(rows[0] if rows else {}))

            elif type_ == "timeseries":
                q = f"""
                SELECT CAST(date AS STRING) AS date,
                    SUM(COALESCE(IMPRESSIONS,0)) AS impressions,
                    SUM(COALESCE(CLICKS_LINK,0)) AS clicks,
                    SUM(COALESCE(THRUPLAY,0))    AS thruplay
                FROM {BQ_TABLE_3}
                WHERE date BETWEEN '{start}' AND '{end}' AND {f}
                GROUP BY date ORDER BY date
                """
                return self._send(json_response({"rows": bq_rows(q)}))

            elif type_ == "by_influencer":
                q = f"""
                SELECT
                    TRIM(COALESCE(NULLIF(TRIM(INFLUENCIADOR),''),NULLIF(TRIM(AD_NAME),''),'Sem Influenciador')) AS influenciador,
                    AD_NAME, AD_GROUP_NAME, platform, CAMPAIGN_NAME,
                    SUM(COALESCE(IMPRESSIONS,0))  AS impressions,
                    SUM(COALESCE(CLICKS_LINK,0))  AS clicks_link,
                    SUM(COALESCE(CLICKS,0))       AS clicks,
                    SUM(COALESCE(THRUPLAY,0))     AS thruplay,
                    SUM(COALESCE(total_comments,0)+COALESCE(total_compartilhamento,0)+COALESCE(total_reacoes,0)+COALESCE(total_salvamentos,0)) AS engagement,
                    SAFE_DIVIDE(SUM(COALESCE(CLICKS_LINK,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS ctr,
                    SAFE_DIVIDE(SUM(COALESCE(THRUPLAY,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS vtr,
                    SAFE_DIVIDE(
                        SUM(COALESCE(total_comments,0)+COALESCE(total_compartilhamento,0)+COALESCE(total_reacoes,0)+COALESCE(total_salvamentos,0)),
                        NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0)
                    )*100 AS engagement_rate
                FROM {BQ_TABLE_3}
                WHERE date BETWEEN '{start}' AND '{end}' AND {f}
                GROUP BY influenciador, AD_NAME, AD_GROUP_NAME, platform, CAMPAIGN_NAME
                ORDER BY impressions DESC
                """
                return self._send(json_response({"rows": bq_rows(q)}))

            elif type_ == "by_campaign":
                q = f"""
                SELECT platform, CAMPAIGN_NAME,
                    SUM(COALESCE(IMPRESSIONS,0))  AS impressions,
                    SUM(COALESCE(CLICKS_LINK,0))  AS clicks_link,
                    SUM(COALESCE(CLICKS,0))       AS clicks,
                    SUM(COALESCE(THRUPLAY,0))     AS thruplay,
                    SUM(COALESCE(total_comments,0)+COALESCE(total_compartilhamento,0)+COALESCE(total_reacoes,0)+COALESCE(total_salvamentos,0)) AS engagement,
                    SAFE_DIVIDE(SUM(COALESCE(CLICKS_LINK,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS ctr,
                    SAFE_DIVIDE(
                        SUM(COALESCE(total_comments,0)+COALESCE(total_compartilhamento,0)+COALESCE(total_reacoes,0)+COALESCE(total_salvamentos,0)),
                        NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0)
                    )*100 AS engagement_rate
                FROM {BQ_TABLE_3}
                WHERE date BETWEEN '{start}' AND '{end}' AND {f}
                GROUP BY platform, CAMPAIGN_NAME ORDER BY impressions DESC
                """
                return self._send(json_response({"rows": bq_rows(q)}))

            elif type_ == "cost":
                q = f"""
                SELECT SUM(COALESCE(total_cost,0)) AS total_cost,
                       SUM(COALESCE(total_alcance,0)) AS total_alcance
                FROM {BQ_TABLE_1}
                WHERE DATE BETWEEN '{start}' AND '{end}' AND {f}
                """
                rows = bq_rows(q)
                return self._send(json_response(rows[0] if rows else {}))

            elif type_ == "reach":
                q = f"""
                SELECT CAST(DATE AS STRING) AS date,
                       SUM(COALESCE(total_alcance,0)) AS alcance
                FROM {BQ_TABLE_1}
                WHERE DATE BETWEEN '{start}' AND '{end}' AND {f}
                GROUP BY DATE ORDER BY DATE
                """
                return self._send(json_response({"rows": bq_rows(q)}))

            else:
                return self._send(error_response("Tipo inválido."))

        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            tb = traceback.format_exc()
            self._send(error_response(f"ERRO: {str(e)} | TRACEBACK: {tb}", 500))

app = handler
