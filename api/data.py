import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _helpers import get_db, get_token, bq_rows, build_camp_filter, BQ_TABLE_3, BQ_TABLE_1, CORS
import jwt

def handler(request):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS)
    try:
        get_token(dict(request.headers))
        args   = request.args or {}
        start  = args.get('start_date','')
        end    = args.get('end_date','')
        type_  = args.get('type','kpi')
        camp_id= args.get('camp_id','')

        if not start or not end:
            return Response(json.dumps({'error': 'start_date e end_date obrigatórios.'}), 400, CORS)

        # Buscar palavras-chave da campanha
        kws, ex = [], []
        if camp_id:
            conn = get_db(); cur = conn.cursor()
            cur.execute("SELECT kws, ex FROM gestao_camps WHERE id=%s", (camp_id,))
            row = cur.fetchone()
            cur.close(); conn.close()
            if row:
                kws, ex = list(row[0] or []), list(row[1] or [])

        f = build_camp_filter(kws, ex)

        if type_ == 'kpi':
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
                SAFE_DIVIDE(SUM(COALESCE(CLICKS_LINK,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS ctr,
                SAFE_DIVIDE(SUM(COALESCE(THRUPLAY,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS vtr
            FROM {BQ_TABLE_3}
            WHERE date BETWEEN '{start}' AND '{end}' AND {f}
            """
            rows = bq_rows(q)
            return Response(json.dumps(rows[0] if rows else {}), 200, CORS)

        elif type_ == 'timeseries':
            q = f"""
            SELECT CAST(date AS STRING) AS date,
                SUM(COALESCE(IMPRESSIONS,0)) AS impressions,
                SUM(COALESCE(CLICKS_LINK,0)) AS clicks,
                SUM(COALESCE(THRUPLAY,0))    AS thruplay
            FROM {BQ_TABLE_3}
            WHERE date BETWEEN '{start}' AND '{end}' AND {f}
            GROUP BY date ORDER BY date
            """
            return Response(json.dumps({'rows': bq_rows(q)}), 200, CORS)

        elif type_ == 'by_influencer':
            q = f"""
            SELECT
                TRIM(COALESCE(NULLIF(TRIM(INFLUENCIADOR),''),NULLIF(TRIM(AD_NAME),''),'Sem Influenciador')) AS influenciador,
                AD_NAME, platform, CAMPAIGN_NAME,
                SUM(COALESCE(IMPRESSIONS,0))  AS impressions,
                SUM(COALESCE(CLICKS_LINK,0))  AS clicks_link,
                SUM(COALESCE(CLICKS,0))       AS clicks,
                SUM(COALESCE(THRUPLAY,0))     AS thruplay,
                SAFE_DIVIDE(SUM(COALESCE(CLICKS_LINK,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS ctr,
                SAFE_DIVIDE(SUM(COALESCE(THRUPLAY,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS vtr
            FROM {BQ_TABLE_3}
            WHERE date BETWEEN '{start}' AND '{end}' AND {f}
            GROUP BY influenciador, AD_NAME, platform, CAMPAIGN_NAME
            ORDER BY impressions DESC
            """
            return Response(json.dumps({'rows': bq_rows(q)}), 200, CORS)

        elif type_ == 'by_campaign':
            q = f"""
            SELECT platform, CAMPAIGN_NAME,
                SUM(COALESCE(IMPRESSIONS,0))  AS impressions,
                SUM(COALESCE(CLICKS_LINK,0))  AS clicks_link,
                SUM(COALESCE(CLICKS,0))       AS clicks,
                SUM(COALESCE(THRUPLAY,0))     AS thruplay,
                SAFE_DIVIDE(SUM(COALESCE(CLICKS_LINK,0)),NULLIF(SUM(COALESCE(IMPRESSIONS,0)),0))*100 AS ctr
            FROM {BQ_TABLE_3}
            WHERE date BETWEEN '{start}' AND '{end}' AND {f}
            GROUP BY platform, CAMPAIGN_NAME ORDER BY impressions DESC
            """
            return Response(json.dumps({'rows': bq_rows(q)}), 200, CORS)

        elif type_ == 'cost':
            q = f"""
            SELECT SUM(COALESCE(total_cost,0)) AS total_cost,
                   SUM(COALESCE(total_alcance,0)) AS total_alcance
            FROM {BQ_TABLE_1}
            WHERE DATE BETWEEN '{start}' AND '{end}' AND {f}
            """
            rows = bq_rows(q)
            return Response(json.dumps(rows[0] if rows else {}), 200, CORS)

        elif type_ == 'reach':
            q = f"""
            SELECT CAST(DATE AS STRING) AS date,
                   SUM(COALESCE(total_alcance,0)) AS alcance
            FROM {BQ_TABLE_1}
            WHERE DATE BETWEEN '{start}' AND '{end}' AND {f}
            GROUP BY DATE ORDER BY DATE
            """
            return Response(json.dumps({'rows': bq_rows(q)}), 200, CORS)

        else:
            return Response(json.dumps({'error': 'Tipo inválido.'}), 400, CORS)

    except (PermissionError, jwt.ExpiredSignatureError) as e:
        return Response(json.dumps({'error': str(e)}), 401, CORS)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), 500, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
