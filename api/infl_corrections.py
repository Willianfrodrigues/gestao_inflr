import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _helpers import get_db, get_token, CORS
import jwt

def handler(request):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS)
    try:
        get_token(dict(request.headers))
        conn = get_db(); cur = conn.cursor()
        camp_id = (request.args or {}).get('camp_id', '')

        if request.method == 'GET':
            if camp_id:
                cur.execute("SELECT ad_name, nome_correto FROM gestao_infl_corrections WHERE camp_id=%s", (camp_id,))
            else:
                cur.execute("SELECT ad_name, nome_correto FROM gestao_infl_corrections")
            rows = cur.fetchall()
            cur.close(); conn.close()
            return Response(json.dumps({r[0]: r[1] for r in rows}), 200, CORS)

        body = request.json
        if body.get('nome_correto'):
            cur.execute("""
                INSERT INTO gestao_infl_corrections (camp_id, ad_name, ad_group, nome_correto)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (camp_id, ad_name) DO UPDATE SET
                    nome_correto=EXCLUDED.nome_correto,
                    ad_group=EXCLUDED.ad_group,
                    updated_at=NOW()
            """, (body['camp_id'], body['ad_name'], body.get('ad_group',''), body['nome_correto']))
        else:
            cur.execute(
                "DELETE FROM gestao_infl_corrections WHERE camp_id=%s AND ad_name=%s",
                (body['camp_id'], body['ad_name'])
            )
        conn.commit(); cur.close(); conn.close()
        return Response(json.dumps({'ok': True}), 200, CORS)

    except (PermissionError, jwt.ExpiredSignatureError) as e:
        return Response(json.dumps({'error': str(e)}), 401, CORS)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), 500, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
