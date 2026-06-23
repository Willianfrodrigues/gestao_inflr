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
            cur.execute("""
                SELECT id,nome,client_id,kws,ex,ini,fim,clk,plt,
                       cpm_cli,investimento,meta_imp,org_ativo,org_url
                FROM gestao_camps ORDER BY nome
            """)
            rows = cur.fetchall()
            cur.close(); conn.close()
            return Response(json.dumps([{
                'id':r[0],'nome':r[1],'cid':r[2],'kws':list(r[3] or []),'ex':list(r[4] or []),
                'ini':str(r[5]) if r[5] else '','fim':str(r[6]) if r[6] else '',
                'clk':r[7],'plt':list(r[8] or []),'cpmCli':float(r[9] or 0),
                'investimento':float(r[10] or 0),'metaImp':int(r[11] or 0),
                'orgAtivo':r[12],'orgUrl':r[13] or ''
            } for r in rows]), 200, CORS)

        body = request.json

        if request.method == 'POST':
            cid = body.get('id') or f"p{int(time.time()*1000)}"
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
                cid, body['nome'], body['cid'],
                body.get('kws',[]), body.get('ex',[]),
                body.get('ini') or None, body.get('fim') or None,
                body.get('clk','clicks_link'), body.get('plt',['meta']),
                body.get('cpmCli',0), body.get('investimento',0),
                body.get('metaImp',0), body.get('orgAtivo',False), body.get('orgUrl','')
            ))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True, 'id': cid}), 200, CORS)

        if request.method == 'DELETE':
            cur.execute("DELETE FROM gestao_camps WHERE id=%s", (body['id'],))
            conn.commit(); cur.close(); conn.close()
            return Response(json.dumps({'ok': True}), 200, CORS)

    except (PermissionError, jwt.ExpiredSignatureError) as e:
        return Response(json.dumps({'error': str(e)}), 401, CORS)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), 500, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
