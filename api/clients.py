import json, time
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
            cur.execute("SELECT id,nome,emp,username,cor,logo,mets FROM gestao_clients ORDER BY nome")
            rows = cur.fetchall()
            cur.close(); conn.close()
            self._send(json_response([{
                "id":r[0],"nome":r[1],"emp":r[2],"user":r[3],
                "cor":r[4],"logo":r[5],"mets":list(r[6] or [])
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
            cid    = body.get("id") or f"c{int(time.time()*1000)}"
            conn = get_db(); cur = conn.cursor()
            cur.execute("""
                INSERT INTO gestao_clients (id,nome,emp,username,password,cor,logo,mets)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, emp=EXCLUDED.emp, username=EXCLUDED.username,
                    cor=EXCLUDED.cor, logo=EXCLUDED.logo, mets=EXCLUDED.mets
            """, (cid, body["nome"], body.get("emp",""), body.get("user",""),
                  body.get("pw","inflr2026"), body.get("cor","#2DD9C0"),
                  body.get("logo"), body.get("mets",[])))
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True, "id": cid}))
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
            cur.execute("DELETE FROM gestao_clients WHERE id=%s", (body["id"],))
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True}))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))
