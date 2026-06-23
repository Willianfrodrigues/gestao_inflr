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

        if request.method == 'GET':
            cur.execute("SELECT id,username,nome,role,perms FROM gestao_users ORDER BY id")
            rows = cur.fetchall()
            cur.close(); conn.close()
            return Response(json.dumps([{
                'id':r[0],'username':r[1],'nome':r[2],'role':r[3],'perms':list(r[4] or [])
            } for r in rows]), 200, CORS)

        body = request.json

        if request.method == 'POST':
            cur.execute("""
                INSERT INTO gestao_users (username,password,nome,role,perms)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING
            """, (body['username'], body['password'], body.get('nome',''),
                  body.get('role','viewer'), body.get('perms',[])))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True}), 200, CORS)

        if request.method == 'PUT':
            cur.execute("""
                UPDATE gestao_users SET nome=%s,role=%s,perms=%s WHERE username=%s
            """, (body.get('nome',''), body.get('role','viewer'),
                  body.get('perms',[]), body['username']))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True}), 200, CORS)

        if request.method == 'DELETE':
            cur.execute("DELETE FROM gestao_users WHERE username=%s AND role!='admin'", (body['username'],))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True}), 200, CORS)

    except (PermissionError, jwt.ExpiredSignatureError) as e:
        return Response(json.dumps({'error': str(e)}), 401, CORS)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), 500, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
