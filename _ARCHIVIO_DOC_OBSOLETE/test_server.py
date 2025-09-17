#!/usr/bin/env python3
"""
Server locale per test con test_finale.html
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse

PORT = 8000

# Carica i dati
with open('MAPPATURE_EXCEL_PERFETTE.json', 'r', encoding='utf-8') as f:
    dati = json.load(f)

CATEGORIA_EVENTI_MAP = dati['mappature_categoria_eventi']
EVENT_DESCRIPTIONS = dati['vlookup_map']

print(f"✓ Caricate {len(CATEGORIA_EVENTI_MAP)} categorie")
print(f"✓ Caricate {len(EVENT_DESCRIPTIONS)} descrizioni")

class RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/categories':
            response = {
                'categories': list(CATEGORIA_EVENTI_MAP.keys()),
                'total': len(CATEGORIA_EVENTI_MAP)
            }
            
        elif path.startswith('/events/'):
            categoria = urllib.parse.unquote(path.replace('/events/', ''))
            
            if categoria in CATEGORIA_EVENTI_MAP:
                eventi = CATEGORIA_EVENTI_MAP[categoria]
                response = {
                    'category': categoria,
                    'events': eventi,
                    'total': len(eventi)
                }
            else:
                response = {'error': f'Categoria non trovata: {categoria}'}
                
        elif path.startswith('/description/'):
            evento = urllib.parse.unquote(path.replace('/description/', ''))
            
            if evento in EVENT_DESCRIPTIONS:
                response = {
                    'event_code': evento,
                    'description': EVENT_DESCRIPTIONS[evento]
                }
            else:
                response = {'event_code': evento, 'description': None}
        else:
            response = {'error': 'Endpoint non trovato'}
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Silenzioso

print(f"\n✅ SERVER TEST su http://localhost:{PORT}")
print("Apri test_finale.html nel browser!")
print("Ctrl+C per fermare\n")

httpd = HTTPServer(('', PORT), RequestHandler)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServer fermato.")