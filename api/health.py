import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _helpers import CORS

def handler(request):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS)
    return Response(json.dumps({'status': 'ok', 'service': 'inflr-gestao'}), 200, CORS)

class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body; self.status_code = status; self.headers = headers or {}
