#!/usr/bin/env python3
"""
SERVER SEMPLICE PER SISTEMA EXCEL - Senza dipendenze esterne
Usa solo librerie standard Python
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse

# Porta del server
PORT = 8000

# MAPPING CATEGORIE -> EVENTI (dal foglio 'work' dell'Excel)
CATEGORIA_EVENTI_MAP = {
    "Internal_Fraud_Frodi_interne": [
        "601 - Furto di denaro, cassa o altro",
        "602 - Furto di beni/merce di proprietà della banca o clienti",
        "603 - Distruzione fraudolenta di beni di proprietà della banca",
        "604 - Falsificazione di documentazione",
        "605 - Frode informatica con danni",
        "606 - Furto di info sensibili/violazione privacy con danni (violazione interna dolosa)",
        "607 - Movimentazione non autorizzata di conti / posizioni",
        "608 - Insider trading / manipolazione mercato",
        "609 - Intenzionale errata marcatura posizioni",
        "610 - Frode creditizia interna",
        "611 - Appropriazione indebita",
        "612 - Mazzette/tangenti ricevute o date",
        "613 - Utilizzo insider information per profitto personale",
        "614 - Errata valutazione deliberata di strumenti, crediti o posizioni",
        "615 - Violazione della normativa sulla concorrenza",
        "616 - Utilizzo di servizi/beni aziendali per fini personali",
        "617 - Danno deliberato ai sistemi informativi",
        "618 - Mancata applicazione deliberata del sistema dei controlli interni",
        "619 - Altri eventi di frode interna o furto/sottrazione"
    ],
    "External_fraud_Frodi_esterne": [
        "701 - Furto o rapina",
        "702 - Falsificazione",
        "703 - Assegni scoperti",
        "704 - Frode informatica",
        "705 - Phishing o furto di informazioni sensibili",
        "706 - Attacco fisico alle infrastrutture",
        "707 - Attacco ai sistemi informativi",
        "708 - Frode creditizia esterna",
        "709 - Frode su carte pagamento",
        "710 - Riciclaggio o finanziamento terrorismo",
        "711 - Furto o manomissione di ATM (con o senza skimming)",
        "712 - Frode su addebito diretto",
        "713 - Falsa identità (identity theft)",
        "714 - Hackeraggio/compromissione dei conti",
        "715 - Spoofing / Pharming",
        "716 - Furto di info riservate (es. codici, PIN)",
        "717 - Altri eventi di frode esterna"
    ],
    "Employment_practices_Dipendenti": [
        "201 - Compensazione, benefit, dismissione del dipendente",
        "202 - Rescissione rapporto lavoro, vertenza sindacale",
        "203 - Lavoro dipendenti disabili",
        "204 - Azioni di mobbing",
        "205 - Discriminazione",
        "206 - Azioni sindacali interne",
        "207 - Salute e sicurezza sul lavoro",
        "208 - Organizzazione del lavoro, ambiente di lavoro",
        "209 - Turnover eccessivo del personale",
        "210 - Dipendenti con competenze inadeguate al ruolo",
        "211 - Responsabilità generale (del datore di lavoro)",
        "212 - Contenzioso giuslavoristico generale",
        "213 - Infortuni sul lavoro",
        "214 - Stress da lavoro correlato",
        "215 - Assenteismo elevato o ingiustificato",
        "216 - Violazione GDPR da parte dei dipendenti (non dolosa)",
        "217 - Fuga di informazioni sensibili da parte dei dipendenti (non dolosa)",
        "218 - Errore nell'applicazione delle procedure/policy",
        "219 - Negligenza o errore umano",
        "220 - Conflitto di interesse non dichiarato",
        "221 - Altri problemi dipendenti o di ambiente di lavoro"
    ],
    "Clients_product_Clienti": [
        "301 - Vendita impropria, truffa - Manipolazione mercato",
        "302 - Antitrust",
        "303 - Trading improprio",
        "304 - Abuso informazioni confidenziali clienti / violazione privacy",
        "305 - Violazione privacy",
        "306 - Vendita impropria / errate comunicazioni commerciali",
        "307 - Violazione fiduciaria",
        "308 - Suitability / Disclosure issues",
        "309 - Churning / cross-selling aggressivo",
        "310 - Superamento limiti sui clienti (non intenzionale)",
        "311 - Pratiche aggressive di vendita, vendita forzata, pratiche commerciali scorrette",
        "312 - Errata consulenza d'investimento",
        "313 - Pubblicità ingannevole",
        "314 - Inefficienza nella gestione reclami",
        "315 - Mancanza trasparenza o disclosure",
        "316 - Violazione normativa market abuse",
        "317 - Conflitto di interesse nella prestazione del servizio",
        "318 - Violazione normativa antiriciclaggio",
        "319 - Mancato rispetto MiFID",
        "320 - Sottrazione dati personali o breach",
        "321 - Diffusione non autorizzata informazioni su clienti",
        "322 - Mancato rispetto requisiti ESG",
        "323 - Violazione normativa relativa a tassi e commissioni",
        "324 - Greenwashing",
        "325 - Sottrazione di denaro o beni dei clienti",
        "326 - Errata gestione dei dati dei clienti",
        "327 - Inadeguata profilazione clientela",
        "328 - Inadeguata rendicontazione verso i clienti",
        "329 - Offerta di prodotti non autorizzati",
        "330 - Discriminazione nelle pratiche di vendita",
        "331 - Informazioni fuorvianti su prodotti finanziari",
        "332 - Violazione disciplina credito al consumo",
        "333 - Mancata aderenza a standard di mercato",
        "334 - Reputazionale legato alla clientela",
        "335 - Altri difetti prodotto / pratiche commerciali",
        "336 - Altri difetti advisory",
        "337 - Altri reclami per difetto di selezione, sponsorizzazione ed esposizione",
        "338 - Altri eventi violazione fiduciaria",
        "339 - Selezione, sponsorizzazione ed esposizione",
        "340 - Attività di advisory",
        "341 - Altri eventi legati a clienti, prodotti, pratiche professionali",
        "342 - Difetti del prodotto (design difettoso, errato uso dati storici o di modello)",
        "343 - Pratiche commerciali"
    ],
    "Damage_Danni": [
        "501 - Perdite dovute a catastrofi naturali",
        "502 - Danni ad attività materiali per altri eventi esterni",
        "503 - Terremoto",
        "504 - Alluvione",
        "505 - Incendio",
        "506 - Inondazione da rottura tubature",
        "507 - Terrorismo",
        "508 - Vandalismo",
        "509 - Crollo edifici",
        "510 - Eventi atmosferici estremi",
        "511 - Altri danni ad attività materiali"
    ],
    "Business_disruption": [
        "401 - Problemi hw informatici non intenzionali",
        "402 - Problemi sw (inclusi quelli creati dagli aggiornamenti) non intenzionali",
        "403 - Problemi telecomunicazioni",
        "404 - Interruzione elettricità, interruzione/guasto utility",
        "405 - Cyber attack (DDoS e altri)",
        "406 - Malware, virus informatici, spyware",
        "407 - Ransomware",
        "408 - Cryptojacking",
        "409 - Data breach, violazioni della sicurezza informatica",
        "410 - Problemi con i data center",
        "411 - Problemi con servizi cloud",
        "412 - Obsolescenza tecnologica",
        "413 - Errori nelle interfacce tra sistemi",
        "414 - Bug di sicurezza nei software",
        "415 - Vulnerabilità zero-day",
        "416 - Interruzione dei servizi internet",
        "417 - Indisponibilità dei sistemi di backup",
        "418 - Disaster recovery inadeguato",
        "419 - Dipendenza eccessiva da singoli fornitori IT",
        "420 - Altri eventi business disruption o problemi di sistema"
    ],
    "Execution_delivery_Problemi_di_produzione_o_consegna": [
        "101 - Comunicazione errata",
        "102 - Inserimento dati, manutenzione/caricamento - Errore data entry",
        "103 - Mancato rispetto di deadline, scadenze fiscali",
        "104 - System misoperation - Errore sistema",
        "105 - Accounting error / errore attribuzione entità",
        "106 - Altro errore di esecuzione",
        "107 - Consegna fallita (esecuzione incompleta)",
        "108 - Mancato regolamento nei tempi previsti",
        "109 - Collateral management failure",
        "110 - Reference data maintainance",
        "111 - Mandatory reporting inaccurato o ommesso",
        "112 - Perdite per tassazione imprecisa/errata del cliente",
        "113 - Altro errore di consegna",
        "114 - Introduzione cliente con data incompleta",
        "115 - Autorizzazione/rifiuto errato di danni a cliente",
        "116 - Altre perdite del cliente",
        "117 - Performance controparte non finanziaria",
        "118 - Altre controversie controparte non finanziaria",
        "119 - Consegna incompleta o inaccurata info su progetti di outsourcing",
        "120 - Vendors & Suppliers dispute - outsourcing",
        "121 - Altri eventi gestione processo e esecuzione",
        "122 - Incorretta approvazione cliente",
        "123 - Documenti legali mancanti / incompleti",
        "124 - Non autorizzazione ai clienti oltre limiti approvati",
        "125 - Altri eventi client permission / esclusioni / disclaimer",
        "126 - Produzione di report errata esterna",
        "127 - Altri eventi reporting obbligatorio",
        "128 - Controparti commerciali",
        "129 - Vendors e suppliers",
        "130 - Errori di calcolo nei modelli",
        "131 - Errori nei processi di riconciliazione",
        "132 - Problemi di interfaccia tra sistemi",
        "133 - Errata gestione dei flussi documentali",
        "134 - Mancata chiusura posizioni",
        "135 - Errori nella gestione delle garanzie",
        "136 - Errata valorizzazione di strumenti finanziari",
        "137 - Problemi di segregazione dei compiti",
        "138 - Carenza nei controlli di primo livello",
        "139 - Inadeguata documentazione dei processi",
        "140 - Mancato rispetto delle procedure operative",
        "141 - Errori nella migrazione dati",
        "142 - Interruzione della catena di approvvigionamento",
        "143 - Mancata esecuzione ordini clienti",
        "144 - Errori nei processi di fatturazione",
        "145 - Problemi di qualità dei dati",
        "146 - Mancata verifica KYC/AML",
        "147 - Errata gestione della documentazione contrattuale",
        "148 - Ritardi nei processi di clearing & settlement",
        "149 - Mancato matching delle transazioni",
        "150 - Errori nel processo di onboarding clienti",
        "151 - Problemi nell'archiviazione documentale",
        "152 - Errori nella gestione dei pagamenti",
        "153 - Mancato rispetto SLA interni",
        "154 - Inadeguata supervisione dei processi",
        "155 - Errori nella trasmissione ordini",
        "156 - Problemi di capacity planning",
        "157 - Mancata segregazione dei conti clienti",
        "158 - Errori nella gestione corporate actions",
        "159 - Registrazione dati di scarsa qualità (data quality)"
    ]
}

# DESCRIZIONI EVENTI (VLOOKUP)
EVENT_DESCRIPTIONS = {
    "601 - Furto di denaro, cassa o altro": "Sottrazione illecita di denaro contante o altri valori dalla cassa aziendale",
    "701 - Furto o rapina": "Eventi di furto o rapina perpetrati da soggetti esterni",
    "201 - Compensazione, benefit, dismissione del dipendente": "Problematiche relative a retribuzione, benefit e licenziamenti",
    "301 - Vendita impropria, truffa - Manipolazione mercato": "Vendita inappropriata di prodotti o manipolazione del mercato",
    "401 - Problemi hw informatici non intenzionali": "Malfunzionamenti hardware non intenzionali dei sistemi informatici",
    "501 - Perdite dovute a catastrofi naturali": "Perdite causate da eventi naturali catastrofici",
    "101 - Comunicazione errata": "Errori nella comunicazione interna o esterna che causano perdite"
}

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def do_GET(self):
        """Handle GET requests"""
        # Parse URL
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Route: /categories
        if path == '/categories':
            response = {
                "categories": list(CATEGORIA_EVENTI_MAP.keys()),
                "total": len(CATEGORIA_EVENTI_MAP)
            }
            self.wfile.write(json.dumps(response).encode())
            
        # Route: /events/<category>
        elif path.startswith('/events/'):
            category = urllib.parse.unquote(path.split('/events/')[1])
            if category in CATEGORIA_EVENTI_MAP:
                events = CATEGORIA_EVENTI_MAP[category]
                response = {
                    "category": category,
                    "events": events,
                    "total": len(events)
                }
            else:
                response = {"error": "Category not found"}
            self.wfile.write(json.dumps(response).encode())
            
        # Route: /description/<event_code>
        elif path.startswith('/description/'):
            event_code = urllib.parse.unquote(path.split('/description/')[1])
            # Cerca la descrizione (simulazione VLOOKUP)
            description = EVENT_DESCRIPTIONS.get(event_code, f"Descrizione per {event_code}")
            response = {
                "event_code": event_code,
                "description": description
            }
            self.wfile.write(json.dumps(response).encode())
            
        # Route: /
        elif path == '/':
            response = {
                "status": "Sistema Excel API attivo",
                "endpoints": [
                    "/categories - Lista categorie",
                    "/events/<category> - Eventi per categoria",
                    "/description/<event_code> - Descrizione evento"
                ]
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def log_message(self, format, *args):
        """Override to show cleaner logs"""
        print(f"[{self.address_string()}] {format % args}")

def run_server():
    """Avvia il server"""
    print("="*60)
    print("🚀 EXCEL SYSTEM SERVER (Versione Semplice)")
    print("="*60)
    print(f"Server in ascolto su http://localhost:{PORT}")
    print("\nEndpoints disponibili:")
    print("  GET /categories - Lista categorie")
    print("  GET /events/<category> - Eventi filtrati per categoria")
    print("  GET /description/<event> - Descrizione evento (VLOOKUP)")
    print("\n✅ Apri test_finale.html nel browser per testare!")
    print("="*60)
    
    server = HTTPServer(('localhost', PORT), SimpleHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Server fermato")
        server.shutdown()

if __name__ == "__main__":
    run_server()