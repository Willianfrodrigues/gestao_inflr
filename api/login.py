import json
from http.server import BaseHTTPRequestHandler
from _helpers import get_db, make_token, init_db, json_response, error_response, cors_headers

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

    def do_POST(self):
        try:
            init_db()
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            username = (body.get("username") or "").strip()
            password = (body.get("password") or "").strip()

            conn = get_db(); cur = conn.cursor()

            # 1. Tentar login como admin (gestao_users)
            cur.execute(
                "SELECT id, username, nome, role, perms FROM gestao_users WHERE username=%s AND password=%s",
                (username, password)
            )
            row = cur.fetchone()

            if row:
                user  = {"id": row[0], "username": row[1], "nome": row[2], "role": row[3], "perms": list(row[4] or [])}
                token = make_token(user)
                cur.close(); conn.close()
                return self._send(json_response({**user, "token": token}))

            # 2. Tentar login como cliente (gestao_clients)
            cur.execute(
                "SELECT id, username, nome, cor FROM gestao_clients WHERE username=%s AND password=%s",
                (username, password)
            )
            row = cur.fetchone()
            cur.close(); conn.close()

            if not row:
                return self._send(error_response("Usuário ou senha incorretos.", 401))

            user = {
                "id":       row[0],
                "username": row[1],
                "nome":     row[2],
                "role":     "client",
                "cor":      row[3],
                "perms":    ["cliente-view"]
            }
            token = make_token(user)
            self._send(json_response({**user, "token": token}))

        except Exception as e:
            self._send(error_response(str(e), 500))

app = handler
