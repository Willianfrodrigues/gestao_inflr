import json
import jwt
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
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
            parsed  = urlparse(self.path)
            params  = parse_qs(parsed.query)
            camp_id = params.get("camp_id", [""])[0]
            conn = get_db(); cur = conn.cursor()
            if camp_id:
                cur.execute("SELECT ad_name, nome_correto FROM gestao_infl_corrections WHERE camp_id=%s", (camp_id,))
            else:
                cur.execute("SELECT ad_name, nome_correto FROM gestao_infl_corrections")
            rows = cur.fetchall()
            cur.close(); conn.close()
            self._send(json_response({r[0]: r[1] for r in rows}))
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
            if body.get("nome_correto"):
                cur.execute("""
                    INSERT INTO gestao_infl_corrections (camp_id, ad_name, ad_group, nome_correto)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (camp_id, ad_name) DO UPDATE SET
                        nome_correto=EXCLUDED.nome_correto,
                        ad_group=EXCLUDED.ad_group,
                        updated_at=NOW()
                """, (body["camp_id"], body["ad_name"], body.get("ad_group",""), body["nome_correto"]))
            else:
                cur.execute(
                    "DELETE FROM gestao_infl_corrections WHERE camp_id=%s AND ad_name=%s",
                    (body["camp_id"], body["ad_name"])
                )
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True}))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))

app = handler
