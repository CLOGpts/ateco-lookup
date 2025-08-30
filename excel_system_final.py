#!/usr/bin/env python3
"""
SISTEMA FINALE - REPLICA ESATTA EXCEL
Categoria → Eventi filtrati → Descrizione automatica
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json

app = FastAPI(title="Excel Risk System - FINALE", version="1.0.0")

# CORS per il frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carica i dati REALI dall'Excel
try:
    with open('excel_data_complete.json', 'r', encoding='utf-8') as f:
        EXCEL_DATA = json.load(f)
    
    with open('excel_lookups_complete.json', 'r', encoding='utf-8') as f:
        EXCEL_LOOKUPS = json.load(f)
        
    print("✅ Dati Excel caricati correttamente!")
except Exception as e:
    print(f"❌ Errore caricamento: {e}")
    EXCEL_DATA = {}
    EXCEL_LOOKUPS = {"data": {}}

# MAPPATURA CATEGORIA → EVENTI (dal foglio WORK)
CATEGORIA_EVENTI_MAP = {
    "Internal_Fraud_Frodi_interne": [
        "601 - Furto di denaro, cassa o altro",
        "603 - Transazioni non notificate (intenzionalmente)",
        "604 - Frode mista / collusione",
        "605 - Appropriazione indebita di fondi / titoli, furto e uso fraudolento di altri beni aziendali",
        "606 - Abuso di potere e / o attività non autorizzata (intenzionale)",
        "608 - Eccesso di fiducia / Sfruttamento di debolezza (frode interna)",
        "609 - Distruzione dannosa di beni / Attacco terroristico",
        "610 - Falsificazione, modificazione e contraffazione di documenti / Occultamento intenzionale (escluse le frodi di mercato)",
        "613 - Furto d'identità/uso di account aziendale non proprio (da parte di un dipendente)",
        "614 - Tassazione non versata o evasione",
        "615 - Regole relative gli incentivi (anche regali e inviti ricevuti o dati) non sufficientemente formalizzate e/o rispettate.",
        "618 - Corruzione attiva o passiva (esecutore o complice)",
        "619 - Uso improprio di beni aziendali (autore o complicità)",
        "622 - Appropriazione indebita di fondi, denaro o titoli",
        "623 - Furto di attrezzature",
        "624 - Abuso di mercato (insider trading, manipolazione dei prezzi, diffusione di informazioni false)",
        "626 - Frodi relative ai mezzi di pagamento",
        "628 - Furto e divulgazione di dati (frodi interne)",
        "699 - Altre frodi interne (da utilizzare solo se non è possibile utilizzare un altro codice)"
    ],
    "External_fraud_Frodi_esterne": [
        "701 - Furto / perdita / frode",
        "702 - Danno da hacking",
        "703 - Distruzione di dati (frode esterna)",
        "704 - Attacchi: rapina o furto (denaro o beni)",
        "705 - Frode con carte di credito o prepagate",
        "706 - Altra frode: truffa",
        "707 - Furto e/o divulgazione di dati riservati (frodi esterne)",
        "708 - Falsificazione / contraffazione di documenti (esclusi mezzi di pagamento)",
        "709 - Assegni scoperti o altra forma di mancato pagamento",
        "710 - Sabotaggio",
        "711 - Frodi assicurative (perdite e danni)",
        "712 - Usurpazione / falsa identità (di una terza parte)",
        "713 - Debitore irritracciabile",
        "714 - Possibile effrazione",
        "723 - Abuso di fiducia / Abuso di debolezza (Frode esterna)",
        "799 - Altre frodi esterne (da utilizzare solo se non è possibile utilizzare un altro codice)",
        "213 - Abuso di mercato (insider trading, manipolazione dei prezzi, diffusione di informazioni false) commessi da terzi"
    ],
    "Employment_practices_Dipendenti": [
        "301 - Mancanza di personale, turnover eccessivo",
        "302 - Carenza di norme in termini di salute e sicurezza",
        "303 - Indennità relative al contratto di lavoro (compensi, benefit, licenziamenti ...)",
        "304 - Subappalto illegale e subaffitto di dipendenti non normato",
        "305 - Contenzioso / pagamento dei dipendenti ai dipendenti",
        "306 - Discriminazione o molestie di candidati o dipendenti",
        "307 - Clima aziendale non favorevole",
        "309 - Perdita di un gruppo di lavoro (team) chiave e strategico",
        "310 - Incidenti che coinvolgono la responsabilità dell'azienda",
        "311 - Responsabilità in generale su rischi non dichiarati (scivolata,  caduta, ecc….)",
        "313 - Mancato rispetto delle normative informatiche",
        "314 - Mancato rispetto nei confronti delle unioni dei dipendenti (sindacali, ecc…), alterazione del clima sociale",
        "330 - Mancato rispetto dell'obbligo regolamentare di formare il personale nel rispetto delle norme",
        "332 - Mancato rispetto delle norme sulla tutela della privacy dei dipendenti. Insufficienza di formalizzazione o rispetto delle norme",
        "333 - Retribuzioni medie non in linea con il mercato",
        "334 - Comunicazione interna azienda non adeguata",
        "340 - Inosservanza delle norme sanitarie",
        "341 - Non conformità alle norme di sicurezza sul posto di lavoro",
        "342 - Mancato rispetto del contratto di lavoro e applicazione della politica salariale (indennità, benefici, licenziamenti ...)",
        "343 - Errori riguardo le normative relative al libro paga e altri documenti",
        "399 - Altre questioni relative alla gestione dei dipendenti (da utilizzare solo se non è possibile utilizzare un altro codice)"
    ],
    "Clients_product_Clienti": [
        "501 - Mancato rispetto delle regole di vendita (anche vendite a distanza) / Inosservanza delle regole e delle competenze professionali",
        "502 - Autorizzazione / rifiuto di un pagamento non conforme",
        "503 - Comportamenti o pratiche di vendita impropri",
        "504 - Violazione delle regole fiduciarie",
        "505 - Mancato rispetto delle misure di protezione dei dati o delle informazioni personali dei clienti o altri soggetti terzi (esclusi i collaboratori)",
        "506 - Insufficiente formalizzazione / sistema / Non conformità con le regole in materia di segreto professionale",
        "507 - Mancato rispetto delle regole sui beni non reclamati",
        "508 - Danno reputazionale",
        "509 - Analisi dei bisogni dei clienti",
        "511 - Errori sui modelli e/o prodotti difettosi",
        "512 - Mancata idoneetà prodotti o servizi inadeguati alle esigenze del cliente, controversie",
        "515 - Non conformità alle norme antitrust",
        "516 - Mancata attuazione della politica di prevenzione e gestione dei conflitti di interesse",
        "517 - Regolamentazione professionale: inosservanza delle condizioni per l'esercizio delle attività (autorizzazione, ecc.)",
        "518 - Mancato rispetto delle regole e dei regolamenti interni relativi agli embarghi, al congelamento dei beni e al finanziamento del terrorismo",
        "519 - Due diligence insufficiente (nel contesto della protezione del cliente)",
        "520 - Mancato rispetto della procedura per l'approvazione di nuovi prodotti e nuove attività",
        "521 - Superamento del limite di esposizione del cliente",
        "522 - Uso improprio di informazioni riservate",
        "523 - Mancato rispetto delle misure legali e regolamentari relative agli abusi di mercato",
        "533 - Inosservanza del principio di mettere al primo posto gli interessi del cliente",
        "537 - Rapporti con clienti e transazioni non formalizzate, come richiesto dalle normative (contratti, sicurezza, clausole, fatturazione, ...)",
        "538 - Gestione inadeguata dei malfunzionamenti e/o implementazione di misure correttive.",
        "543 - Mancanza di informazioni sui prodotti e debolezza su informazioni e servizi",
        "544 - Mancato rispetto delle regole e delle condizioni tariffarie",
        "550 - Pubblicità ingannevole",
        "551 - Nessuna gestione relativa il conflitto di interessi",
        "552 - Mancato rispetto (o assenza) delle regole che regolano l'archiviazione e tracciabilità dei dati, le registrazioni telefoniche, ecc...",
        "554 - Mancato rispetto degli obblighi contrattuali, dei termini legali, delle regole di gestione, delle regole formali o delle formalità applicabili ai contratti e alla sicurezza / clausole abusive o fatturazione",
        "555 - Mancato obbligo di informare, avvisare o consigliare il management a fronte di un evento importante",
        "556 - Ristrutturazione di un contratto o di una garanzia",
        "557 - Prodotto con design o specifiche inadeguate",
        "558 - Mancato rispetto delle regole formali o delle formalità applicabili ai contratti, ai garanti e/o garanzie",
        "559 - Clausole abusive o fatturazione errata che può generare contenzioso",
        "561 - Assunzione di titoli e garanzie eccessive o sproporzionate",
        "564 - Abuso di diritto",
        "565 - Fideiussione sproporzionata o fraudolenta",
        "566 - Discriminazione dei clienti e/o scoring non etico",
        "568 - Mancato rispetto delle norme relative all'usura e ai tassi di interesse",
        "570 - Frode in gestione presso un legale",
        "571 - Mancato rispetto delle norme relative ai mezzi di pagamento",
        "575 - Mancato rispetto delle condizioni di vendita e dei regolamenti di trasparenza dei prezzi",
        "599 - Altre cause in relazione alla relazione con il cliente (da utilizzare solo se non è possibile utilizzare un altro codice)",
        "204 - Debolezza o mancanza di conformità tra la politica di remunerazione variabile del personale e l'idoneità dei prodotti venduti ai clienti",
        "208 - Inosservanza nelle norme relatine i sistemi di sorveglianza informatica",
        "211 - Violazione contrattuale",
        "440 - Finanziamento di fatture fittizie o crediti fasulli che creano danno finanziario"
    ],
    "Damage_Danni": [
        "101 - Disastro naturale: fuoco",
        "102 - Meteorologico, geologico e altre catastrofi naturali",
        "103 - Altri disastri naturali",
        "105 - Distruzione e deterioramento doloso di proprietà / atti vandalici",
        "106 - Controversie dovute a beni materiali, infrastrutture o altro",
        "107 - Rischi derivanti da proprietà operative o non operative (possedute o affittate)",
        "108 - Danni accidentali a beni, danni da acqua, danni elettrici ...",
        "109 - Degrado dei mezzi posseduti: un'automobile, furgoni ecc... appartenenti alla società",
        "110 - Danno ad una delle sedi o area produttiva o uffici …",
        "115 - Altri danni a beni materiali"
    ],
    "Business_disruption": [
        "201 - Violazione riguardo l'integrità dei dati aziendali",
        "202 - Errori di programmazione o risultati forniti da applicazioni informatiche inaccurate o incomplete (bug, errori di progettazione o di specifica o incomprensioni ...)",
        "203 - Violazione della sicurezza del software (non intenzionale)",
        "204 - Debolezza o mancanza di conformità tra la politica di remunerazione variabile del personale e l'idoneità dei prodotti venduti ai clienti",
        "205 - Inadeguatezza delle risorse dei computer in termini di potenza elaborativa o di memorizzazione (storage)",
        "206 - Indisponibilità di un servizio aziendale a causa di indisponibilità accidentale o involontaria (perdita, deterioramento, blocco del funzionamento) di una risorsa (hardware, applicazione)",
        "207 - Contenzioso (tecnologia)",
        "209 - Danni causati da un taglio alla rete elettrica, rete di telecomunicazione, collegamenti specializzati, approvvigionamento idrico …",
        "210 - Disfunzione derivante dall'inosservanza dei requisiti legali, professionali ed etici in relazione all'IT",
        "212 - Distruzione o deterioramento irrimediabile dei dati dei computer o server (incidente o errore)",
        "214 - Concorrenti",
        "215 - Ricerca e sviluppo- progresso tecnologico inadeguato",
        "216 - Costi materie prime e/o utility non adeguati al business case iniziale",
        "217 - Oscillazioni cambi e tassi non adeguati al business case iniziale",
        "218 - Ciclo di vita del prodotto non adeguato alle attese del cliente",
        "219 - Proprietà intellettuale non normata o rischio di perdita",
        "299 - Altre cause con origine tecnica (da utilizzare solo se non è possibile utilizzare un altro codice)",
        "450 - Disfunzione derivante dall'obsolescenza di una risorsa (impossibile manutenzione)"
    ],
    "Execution_delivery_Problemi_di_produzione_o_consegna": [
        "401 - Inserimento dati, manutenzione o errori di caricamento",
        "402 - Scarsa conformità o cattiva comprensione delle norme",
        "403 - Carenze organizzative e di norme interne, violazioni del controllo interno o decisioni",
        "404 - Errori dovuti all'inadeguatezza dei sistemi informativi ai prodotti bancari o altro di formale",
        "405 - Debolezza o errori nel change management",
        "406 - Problemi di pagamento / regolamento / consegna",
        "407 - Outsourcing",
        "408 - Malfunzionamento nella gestione dei dati aziendali (database, tabelle, riferimenti, ecc...)",
        "409 - Inaccuratezza o imprecisione riguardo report o dati esterni (che causa perdita)",
        "410 - Contenzioso (causato anche da processi, procedure, ecc…)",
        "411 - Insuccesso involontario in dichiarazioni contabili, dichiarazioni normative, prudenziali e / o di segnalazione (eccetto disfunzione IT)",
        "412 - Altre pendenze a causa di processi e procedure",
        "413 - Mancanza di autorizzazioni / esclusione di responsabilità del cliente",
        "414 - Mancato rilevamento e aggiornamento dei dati",
        "415 - Documenti legali mancanti / incompleti",
        "416 - Dati clienti errati o incompleti",
        "417 - Perdita per negligenza o altro danno riguardo le risorse del cliente",
        "418 - Errore o perdita di business, di una controparte cliente o non cliente, escluso ciò che è coperto da garanzia o assicurazione",
        "419 - Controversie con controparti non clienti",
        "420 - Controversie con i fornitori",
        "421 - Errore nella gestione o impostazione di un modello / sistema o processo di calcolo",
        "422 - Errore contabile (Escluso errore durante una transazione su un account cliente)",
        "423 - Mancato monitoraggio o gestione di una garanzia",
        "424 - Mancato scambio o trasmissione di informazioni e / o comunicazioni",
        "425 - Mancato rispetto delle scadenze o identificazione delle responsabilità",
        "426 - Mancato rispetto degli obblighi per lo scambio di informazioni essenziali",
        "427 - Errore nell'attuazione di una vigilanza interna costante, adattata al livello e alla natura dei rischi considerati nel processo",
        "428 - Errore nel sistema di generazione, controllo ed elaborazione delle segnalazioni relative il riciclaggio di denaro / finanziamento del terrorismo e obblighi normativi",
        "429 - Errori nella gestione degli elenchi di clienti, fornitori, dipendenti, non clienti e altre terze parti (con possibili sanzioni)",
        "430 - Errore nella gestione delle transazioni finanziarie",
        "431 - Mancato rispetto del processo e/o mancato rispetto della gestione dei reclami del cliente",
        "432 - Mancanza di clausole formali che disciplinano l'esternalizzazione di processi importanti",
        "433 - Mancato aggiornamento delle informazioni e dei documenti del cliente.",
        "434 - Mancato recupero e aggiornamento di informazioni e documentazione relative all'identificazione e alla conoscenza del cliente",
        "435 - Mancata analisi dei dati e/o dei rischi",
        "436 - Errore di immissione di dati",
        "437 - Mancanza di dati, contratti e formalizzazione di documenti legali",
        "438 - Errore nella gestione degli aggiormanenti, errore di elaborazione o mancata consegna",
        "439 - Mancato rispetto delle procedure e/o deleghe (non intenzionale)",
        "441 - Mancato rispetto delle regole di idoneità del cliente ad un prodotto, eccetto problemi di conoscenza del cliente e malfunzionamenti IT",
        "442 - Carenze organizzative durante l'implementazione di modifiche importanti (gestione della conoscenza, autorizzazioni)",
        "443 - Mancato progettazione o formalizzazione delle procedure",
        "445 - Mancato servizio o/e violazione di un obbligo di legge",
        "446 - Contrattualizzazione non in linea con \"fornitori Strategici\" (FOI: Funzioni Operative Importanti)",
        "447 - Insuccesso nella realizzazione di un servizio da parte di un FOI o/e violazione di un obbligo",
        "448 - Errore monitoraggio di una FOI",
        "451 - Mancato aggiornamento delle informazioni diffuse su Internet e/o mancato rispetto delle regole relative al diritto dell'immagine",
        "452 - Mancata analisi dei dati e/o dei rischi",
        "453 - Errori o dimenticanze riguardo le normative fiscali",
        "454 - Errore nel processo di archiviazione, tracciabilità e conservazione dei dati",
        "455 - Mancato rispetto dei termini del contratto, contrattazione non conforme e/o violazione abusiva del contratto con fornitori, controparti non clienti (escluso FOI)",
        "458 - Inadeguatezza nell'esercizio del controllo regolamentare",
        "459 - Mancato rispetto delle regole per allarmi e whistle blowing, Insufficienza nel sistema per segnalare malfunzionamenti, Mancato rispetto della procedura di escalation",
        "460 - Errori nelle registrazioni in relazione a terzi esclusi i clienti (fornitori, altre terze parti)",
        "461 - Bassa performance della controparte non cliente",
        "499 - Altre cause dovute a \"Execution_delivery\" (Trattamenti e Procedure (da utilizzare solo se non è possibile utilizzare altri codici))"
    ]
}

# Tutti gli eventi con descrizioni (per VLOOKUP)
EVENTI_DESCRIZIONI = EXCEL_DATA.get("events_lookup", {})

@app.get("/")
async def root():
    return {
        "message": "Excel Risk System - FINALE",
        "total_categories": len(CATEGORIA_EVENTI_MAP),
        "total_events": sum(len(events) for events in CATEGORIA_EVENTI_MAP.values())
    }

@app.get("/categories")
async def get_categories():
    """Ritorna tutte le categorie di rischio"""
    return {
        "categories": list(CATEGORIA_EVENTI_MAP.keys())
    }

@app.get("/events/{category}")
async def get_events_by_category(category: str):
    """Ritorna gli eventi per una specifica categoria"""
    if category not in CATEGORIA_EVENTI_MAP:
        raise HTTPException(status_code=404, detail=f"Categoria '{category}' non trovata")
    
    events = CATEGORIA_EVENTI_MAP[category]
    return {
        "category": category,
        "total": len(events),
        "events": events
    }

@app.get("/description/{event_code}")
async def get_event_description(event_code: str):
    """Ritorna la descrizione di un evento (VLOOKUP)"""
    description = EVENTI_DESCRIZIONI.get(event_code, "")
    
    if not description:
        # Prova a cercare negli eventi senza descrizione
        for cat_events in CATEGORIA_EVENTI_MAP.values():
            if event_code in cat_events:
                description = f"[Descrizione non trovata per: {event_code}]"
                break
    
    return {
        "event_code": event_code,
        "description": description
    }

@app.get("/all-data")
async def get_all_data():
    """Ritorna tutti i dati per debug"""
    return {
        "categories": list(CATEGORIA_EVENTI_MAP.keys()),
        "events_per_category": {
            cat: len(events) for cat, events in CATEGORIA_EVENTI_MAP.items()
        },
        "total_events_with_descriptions": len(EVENTI_DESCRIZIONI)
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*80)
    print("🚀 EXCEL RISK SYSTEM - VERSIONE FINALE")
    print("="*80)
    print(f"✅ Categorie: {len(CATEGORIA_EVENTI_MAP)}")
    for cat, events in CATEGORIA_EVENTI_MAP.items():
        print(f"  • {cat}: {len(events)} eventi")
    print(f"\n✅ Totale eventi: {sum(len(e) for e in CATEGORIA_EVENTI_MAP.values())}")
    print(f"✅ Eventi con descrizioni: {len(EVENTI_DESCRIZIONI)}")
    print("\n📍 Server: http://localhost:8000")
    print("="*80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)