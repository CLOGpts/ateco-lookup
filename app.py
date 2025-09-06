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
                
        elif path == '/risk-assessment-fields':
            # NUOVO ENDPOINT: Fornisce le opzioni per i 5 campi di Perdita Finanziaria
            response = {
                'fields': [
                    {
                        'id': 'impatto_finanziario',
                        'column': 'H',
                        'question': 'Qual è l\'impatto finanziario stimato?',
                        'type': 'select',
                        'options': [
                            'N/A',
                            '0 - 1K€',
                            '1 - 10K€',
                            '10 - 50K€',
                            '50 - 100K€',
                            '100 - 500K€',
                            '500K€ - 1M€',
                            '1 - 3M€',
                            '3 - 5M€'
                        ],
                        'required': True
                    },
                    {
                        'id': 'perdita_economica',
                        'column': 'I',
                        'question': 'Qual è il livello di perdita economica attesa?',
                        'type': 'select_color',
                        'options': [
                            {'value': 'G', 'label': 'Bassa/Nulla', 'color': 'green', 'emoji': '🟢'},
                            {'value': 'Y', 'label': 'Media', 'color': 'yellow', 'emoji': '🟡'},
                            {'value': 'O', 'label': 'Importante', 'color': 'orange', 'emoji': '🟠'},
                            {'value': 'R', 'label': 'Grave', 'color': 'red', 'emoji': '🔴'}
                        ],
                        'required': True
                    },
                    {
                        'id': 'impatto_immagine',
                        'column': 'J',
                        'question': 'L\'evento ha impatto sull\'immagine aziendale?',
                        'type': 'boolean',
                        'options': ['Si', 'No'],
                        'required': True
                    },
                    {
                        'id': 'impatto_regolamentare',
                        'column': 'L',
                        'question': 'Ci sono possibili conseguenze regolamentari o legali civili?',
                        'type': 'boolean',
                        'options': ['Si', 'No'],
                        'description': 'Multe, sanzioni amministrative, cause civili',
                        'required': True
                    },
                    {
                        'id': 'impatto_criminale',
                        'column': 'M',
                        'question': 'Ci sono possibili conseguenze penali?',
                        'type': 'boolean',
                        'options': ['Si', 'No'],
                        'description': 'Denunce penali, procedimenti criminali',
                        'required': True
                    }
                ]
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
    
    def do_POST(self):
        """Gestisce richieste POST per salvare i dati di risk assessment"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/save-risk-assessment':
            # Leggi il body della richiesta
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                # Parse JSON dal body
                data = json.loads(post_data.decode('utf-8'))
                
                # Log dei dati ricevuti
                print("\n📊 RISK ASSESSMENT RICEVUTO:")
                print(f"  Evento: {data.get('event_code')} - {data.get('category')}")
                print(f"  --- PERDITA FINANZIARIA ATTESA ---")
                print(f"  H - Impatto finanziario: {data.get('impatto_finanziario')}")
                print(f"  I - Perdita economica: {data.get('perdita_economica')}")
                print(f"  J - Impatto immagine: {data.get('impatto_immagine')}")
                print(f"  L - Impatto regolamentare: {data.get('impatto_regolamentare')}")
                print(f"  M - Impatto criminale: {data.get('impatto_criminale')}")
                
                # Calcola un risk score basato sui dati
                risk_score = self.calculate_risk_score(data)
                
                # Risposta di successo con analisi
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    'status': 'success',
                    'message': 'Risk assessment salvato',
                    'risk_score': risk_score,
                    'analysis': self.generate_analysis(data, risk_score)
                }
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {'error': 'Endpoint POST non trovato'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def calculate_risk_score(self, data):
        """Calcola un risk score basato sui dati"""
        score = 0
        
        # Impatto finanziario (max 40 punti)
        impatto_map = {
            'N/A': 0, '0 - 1K€': 5, '1 - 10K€': 10, '10 - 50K€': 15,
            '50 - 100K€': 20, '100 - 500K€': 25, '500K€ - 1M€': 30,
            '1 - 3M€': 35, '3 - 5M€': 40
        }
        score += impatto_map.get(data.get('impatto_finanziario', 'N/A'), 0)
        
        # Perdita economica (max 30 punti)
        perdita_map = {'G': 5, 'Y': 15, 'O': 25, 'R': 30}
        score += perdita_map.get(data.get('perdita_economica', 'G'), 0)
        
        # Impatti booleani (10 punti ciascuno)
        if data.get('impatto_immagine') == 'Si': score += 10
        if data.get('impatto_regolamentare') == 'Si': score += 10
        if data.get('impatto_criminale') == 'Si': score += 10
        
        return score
    
    def generate_analysis(self, data, score):
        """Genera un'analisi testuale del rischio"""
        if score >= 70:
            level = "CRITICO"
            action = "Richiede azione immediata"
        elif score >= 50:
            level = "ALTO"
            action = "Priorità alta, pianificare mitigazione"
        elif score >= 30:
            level = "MEDIO"
            action = "Monitorare e valutare opzioni"
        else:
            level = "BASSO"
            action = "Rischio accettabile, monitoraggio standard"
        
        return f"Livello di rischio: {level} (Score: {score}/100). {action}"
    
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