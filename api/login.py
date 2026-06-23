import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _helpers import get_db, make_token, init_db, CORS

def handler(request):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS)
    try:
        init_db()
        body = request.json
        username = (body.get('username') or '').strip()
        password = (body.get('password') or '').strip()
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "SELECT id, username, nome, role, perms FROM gestao_users WHERE username=%s AND password=%s",
            (username, password)
        )
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return Response(json.dumps({'error': 'Usuário ou senha incorretos.'}), 401, CORS)
        user = {'id': row[0], 'username': row[1], 'nome': row[2], 'role': row[3], 'perms': list(row[4] or [])}
        token = make_token({**user})
        return Response(json.dumps({**user, 'token': token}), 200, CORS)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), 500, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
