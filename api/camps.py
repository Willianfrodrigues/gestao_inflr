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
            cur.execute("""
                SELECT id,nome,client_id,kws,ex,ini,fim,clk,plt,
                       cpm_cli,investimento,meta_imp,org_ativo,org_url
                FROM gestao_camps ORDER BY nome
            """)
            rows = cur.fetchall()
            cur.close(); conn.close()
            self._send(json_response([{
                "id":r[0],"nome":r[1],"cid":r[2],"kws":list(r[3] or []),"ex":list(r[4] or []),
                "ini":str(r[5]) if r[5] else "","fim":str(r[6]) if r[6] else "",
                "clk":r[7],"plt":list(r[8] or []),"cpmCli":float(r[9] or 0),
                "investimento":float(r[10] or 0),"metaImp":int(r[11] or 0),
                "orgAtivo":r[12],"orgUrl":r[13] or ""
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
            cid    = body.get("id") or f"p{int(time.time()*1000)}"
            conn = get_db(); cur = conn.cursor()
            cur.execute("""
                INSERT INTO gestao_camps
                    (id,nome,client_id,kws,ex,ini,fim,clk,plt,cpm_cli,investimento,meta_imp,org_ativo,org_url)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, client_id=EXCLUDED.client_id,
                    kws=EXCLUDED.kws, ex=EXCLUDED.ex, ini=EXCLUDED.ini, fim=EXCLUDED.fim,
                    clk=EXCLUDED.clk, plt=EXCLUDED.plt, cpm_cli=EXCLUDED.cpm_cli,
                    investimento=EXCLUDED.investimento, meta_imp=EXCLUDED.meta_imp,
                    org_ativo=EXCLUDED.org_ativo, org_url=EXCLUDED.org_url
            """, (
                cid, body["nome"], body["cid"],
                body.get("kws",[]), body.get("ex",[]),
                body.get("ini") or None, body.get("fim") or None,
                body.get("clk","clicks_link"), body.get("plt",["meta"]),
                body.get("cpmCli",0), body.get("investimento",0),
                body.get("metaImp",0), body.get("orgAtivo",False), body.get("orgUrl","")
            ))
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
            cur.execute("DELETE FROM gestao_camps WHERE id=%s", (body["id"],))
            conn.commit(); cur.close(); conn.close()
            self._send(json_response({"ok": True}))
        except (PermissionError, jwt.ExpiredSignatureError) as e:
            self._send(error_response(str(e), 401))
        except Exception as e:
            self._send(error_response(str(e), 500))
