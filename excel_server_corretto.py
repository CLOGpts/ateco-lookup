#!/usr/bin/env python3
"""
SERVER EXCEL CORRETTO - Con mappature ESATTE dall'Excel
Basato sull'analisi delle righe 1000+ del foglio Analisi As-IS
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse

# Porta del server
PORT = 8000

# Carica i dati CORRETTI dal JSON
print("Caricamento dati corretti da MAPPATURE_EXCEL_PERFETTE.json...")
with open('MAPPATURE_EXCEL_PERFETTE.json', 'r', encoding='utf-8') as f:
    dati = json.load(f)

CATEGORIA_EVENTI_MAP = dati['mappature_categoria_eventi']
EVENT_DESCRIPTIONS = dati['vlookup_map']

print(f"✓ Caricate {len(CATEGORIA_EVENTI_MAP)} categorie")
print(f"✓ Caricate {len(EVENT_DESCRIPTIONS)} descrizioni VLOOKUP")

# Mostra statistiche
for cat, eventi in CATEGORIA_EVENTI_MAP.items():
    if eventi:
        print(f"  {cat}: {len(eventi)} eventi")

class RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Gestisce richieste OPTIONS per CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Gestisce richieste GET"""
        # Parse del path
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Headers CORS
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Router semplice
        if path == '/categories':
            # Restituisci lista categorie
            response = {
                'categories': list(CATEGORIA_EVENTI_MAP.keys()),
                'total': len(CATEGORIA_EVENTI_MAP)
            }
            
        elif path.startswith('/events/'):
            # Estrai categoria dal path
            categoria = urllib.parse.unquote(path.replace('/events/', ''))
            
            if categoria in CATEGORIA_EVENTI_MAP:
                eventi = CATEGORIA_EVENTI_MAP[categoria]
                response = {
                    'category': categoria,
                    'events': eventi,
                    'total': len(eventi)
                }
            else:
                response = {
                    'error': f'Categoria non trovata: {categoria}',
                    'available': list(CATEGORIA_EVENTI_MAP.keys())
                }
                
        elif path.startswith('/description/'):
            # Estrai codice evento dal path
            evento = urllib.parse.unquote(path.replace('/description/', ''))
            
            if evento in EVENT_DESCRIPTIONS:
                response = {
                    'event_code': evento,
                    'description': EVENT_DESCRIPTIONS[evento]
                }
            else:
                response = {
                    'event_code': evento,
                    'description': None,
                    'error': 'Descrizione non trovata'
                }
                
        elif path == '/stats':
            # Statistiche del sistema
            response = {
                'total_categories': len(CATEGORIA_EVENTI_MAP),
                'total_events': sum(len(e) for e in CATEGORIA_EVENTI_MAP.values()),
                'total_descriptions': len(EVENT_DESCRIPTIONS),
                'events_per_category': {
                    cat: len(eventi) for cat, eventi in CATEGORIA_EVENTI_MAP.items()
                }
            }
            
        else:
            # Endpoint non trovato
            response = {
                'error': 'Endpoint non trovato',
                'available_endpoints': [
                    '/categories',
                    '/events/{category}',
                    '/description/{event_code}',
                    '/stats'
                ]
            }
        
        # Invia risposta JSON
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override per log personalizzato"""
        message = format % args
        # Solo log per richieste importanti (non OPTIONS)
        if 'OPTIONS' not in message:
            print(f"[{self.log_date_time_string()}] {message}")

# Avvia il server
def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"\n✅ SERVER EXCEL CORRETTO ATTIVO su http://localhost:{PORT}")
    print("\nEndpoints disponibili:")
    print(f"  http://localhost:{PORT}/categories")
    print(f"  http://localhost:{PORT}/events/Damage_Danni")
    print(f"  http://localhost:{PORT}/events/Business_disruption")
    print(f"  http://localhost:{PORT}/events/Employment_practices_Dipendenti")
    print(f"  http://localhost:{PORT}/events/Execution_delivery_Problemi_di_produzione_o_consegna")
    print(f"  http://localhost:{PORT}/events/Clients_product_Clienti")
    print(f"  http://localhost:{PORT}/events/Internal_Fraud_Frodi_interne")
    print(f"  http://localhost:{PORT}/events/External_fraud_Frodi_esterne")
    print(f"  http://localhost:{PORT}/description/[codice_evento]")
    print(f"  http://localhost:{PORT}/stats")
    print("\nPremi Ctrl+C per fermare il server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer fermato.")

if __name__ == '__main__':
    run_server()