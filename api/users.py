import json
import jwt
from http.server import BaseHTTPRequestHandler
from _helpers import get_db, get_token_from_header, json_response, error_response, cors_headers

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
            conn = get_db(); cur = conn.cursor()
            cur.execute("SELECT id,username,nome,role,perms FROM gestao_users ORDER BY id")
            rows = cur.fetchall()
            cur.close(); conn.close()
            self._send(json_response([{
                "id":r[0],"username":r[1],"nome":r[2],"role":r[3],"perms":list(r[4] or [])
            } for r in rows]))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))

    def do_POST(self):
        try:
            get_token_from_header(self.headers)
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            conn = get_db(); cur = conn.cursor()
            cur.execute("""
                INSERT INTO gestao_users (username,password,nome,role,perms)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING
            """, (body["username"], body["password"], body.get("nome",""),
                  body.get("role","viewer"), body.get("perms",[])))
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True}))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))

    def do_PUT(self):
        try:
            get_token_from_header(self.headers)
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            conn = get_db(); cur = conn.cursor()
            cur.execute("""
                UPDATE gestao_users SET nome=%s,role=%s,perms=%s WHERE username=%s
            """, (body.get("nome",""), body.get("role","viewer"),
                  body.get("perms",[]), body["username"]))
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True}))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))

    def do_DELETE(self):
        try:
            get_token_from_header(self.headers)
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            conn = get_db(); cur = conn.cursor()
            cur.execute("DELETE FROM gestao_users WHERE username=%s AND role!='admin'", (body["username"],))
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True}))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))
