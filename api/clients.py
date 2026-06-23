import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _helpers import get_db, get_token, CORS
import jwt

def handler(request):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS)
    try:
        get_token(dict(request.headers))
        conn = get_db(); cur = conn.cursor()

        if request.method == 'GET':
            cur.execute("SELECT id,nome,emp,username,cor,logo,mets FROM gestao_clients ORDER BY nome")
            rows = cur.fetchall()
            cur.close(); conn.close()
            return Response(json.dumps([{
                'id':r[0],'nome':r[1],'emp':r[2],'user':r[3],
                'cor':r[4],'logo':r[5],'mets':list(r[6] or [])
            } for r in rows]), 200, CORS)

        body = request.json

        if request.method == 'POST':
            cid = body.get('id') or f"c{int(time.time()*1000)}"
            cur.execute("""
                INSERT INTO gestao_clients (id,nome,emp,username,password,cor,logo,mets)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, emp=EXCLUDED.emp, username=EXCLUDED.username,
                    cor=EXCLUDED.cor, logo=EXCLUDED.logo, mets=EXCLUDED.mets
            """, (cid, body['nome'], body.get('emp',''), body.get('user',''),
                  body.get('pw','inflr2026'), body.get('cor','#2DD9C0'),
                  body.get('logo'), body.get('mets',[])))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True, 'id': cid}), 200, CORS)

        if request.method == 'DELETE':
            cur.execute("DELETE FROM gestao_clients WHERE id=%s", (body['id'],))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True}), 200, CORS)

    except (PermissionError, jwt.ExpiredSignatureError) as e:
        return Response(json.dumps({'error': str(e)}), 401, CORS)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), 500, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
