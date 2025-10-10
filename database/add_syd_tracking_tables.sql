-- =====================================================
-- SYD AGENT - Tabelle Tracking Eventi
-- =====================================================
-- Creato: 10 Ottobre 2025
-- Scopo: Aggiungere tracking eventi per Syd Agent omniscient
--
-- IMPORTANTE: Questo script AGGIUNGE solo 2 nuove tabelle
-- NON modifica nessuna tabella esistente!
-- =====================================================

-- =====================================================
-- TABELLA 1: user_sessions
-- =====================================================
-- SCOPO: Traccia le sessioni attive degli utenti
-- ESEMPIO: "Mario loggato alle 14:23, progresso 42%"
-- DIMENSIONE: ~100 righe (1 per sessione attiva)
-- =====================================================

CREATE TABLE IF NOT EXISTS user_sessions (
    -- ID univoco sessione (generato automaticamente)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User ID (email o Firebase UID) - NON legato a tabella users
    -- Usiamo VARCHAR invece di UUID per flessibilità
    user_id VARCHAR(255) NOT NULL,

    -- Session ID univoco (per identificare la sessione)
    session_id UUID NOT NULL UNIQUE,

    -- Quando è iniziata la sessione
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Ultima attività (si aggiorna ad ogni azione)
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Fase corrente del processo
    -- Valori possibili: 'idle', 'ateco_analysis', 'risk_assessment', 'report_generation'
    phase VARCHAR(50) DEFAULT 'idle',

    -- Progresso % (0-100)
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),

    -- Metadati extra (JSON flessibile per dati aggiuntivi)
    metadata JSONB DEFAULT '{}'
);

-- Indici per performance (query veloci)
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON user_sessions(last_activity DESC);

-- Commento tabella (documentazione)
COMMENT ON TABLE user_sessions IS 'Sessioni attive utenti per Syd Agent tracking';
COMMENT ON COLUMN user_sessions.user_id IS 'User identifier (email o Firebase UID)';
COMMENT ON COLUMN user_sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN user_sessions.phase IS 'Current phase: idle, ateco_analysis, risk_assessment, report_generation';
COMMENT ON COLUMN user_sessions.progress IS 'Progress percentage 0-100';

-- =====================================================
-- TABELLA 2: session_events
-- =====================================================
-- SCOPO: Salva TUTTI gli eventi che accadono
-- ESEMPIO: "14:25 - Mario carica ATECO 62.01"
-- DIMENSIONE: ~10,000+ righe (molti eventi per sessione)
-- =====================================================

CREATE TABLE IF NOT EXISTS session_events (
    -- ID univoco evento
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User ID (stesso formato di user_sessions)
    user_id VARCHAR(255) NOT NULL,

    -- Session ID (collega all'evento alla sessione)
    session_id UUID NOT NULL,

    -- Tipo di evento
    -- Esempi: 'ateco_uploaded', 'category_selected', 'risk_evaluated'
    event_type VARCHAR(50) NOT NULL,

    -- Dati dell'evento (JSON flessibile)
    -- Esempio: {"code": "62.01", "source": "manual"}
    event_data JSONB NOT NULL DEFAULT '{}',

    -- Quando è successo l'evento
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indici per query veloci
CREATE INDEX IF NOT EXISTS idx_session_events_user_id ON session_events(user_id);
CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id);
CREATE INDEX IF NOT EXISTS idx_session_events_timestamp ON session_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_type ON session_events(event_type);

-- Indice composito per query comuni "tutti eventi di una sessione ordinati per data"
CREATE INDEX IF NOT EXISTS idx_session_events_user_session_time
    ON session_events(user_id, session_id, timestamp DESC);

-- Commenti tabella
COMMENT ON TABLE session_events IS 'Tutti gli eventi che accadono durante le sessioni utente';
COMMENT ON COLUMN session_events.event_type IS 'Tipo evento: ateco_uploaded, category_selected, risk_evaluated, etc.';
COMMENT ON COLUMN session_events.event_data IS 'Payload JSON con dati specifici evento';

-- =====================================================
-- FOREIGN KEY (Opzionale - Collegamento tra tabelle)
-- =====================================================
-- Collega session_events a user_sessions
-- Se cancelli una sessione, cancella anche i suoi eventi
ALTER TABLE session_events
    ADD CONSTRAINT fk_session_events_session
    FOREIGN KEY (session_id)
    REFERENCES user_sessions(session_id)
    ON DELETE CASCADE;

COMMENT ON CONSTRAINT fk_session_events_session ON session_events
    IS 'Se cancelli sessione, cancella automaticamente i suoi eventi';

-- =====================================================
-- TRIGGER: Aggiorna last_activity automaticamente
-- =====================================================
-- Ogni volta che si inserisce un evento, aggiorna last_activity nella sessione
-- Così sappiamo sempre quando l'utente ha fatto l'ultima azione

CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    -- Trova la sessione e aggiorna last_activity
    UPDATE user_sessions
    SET last_activity = NEW.timestamp
    WHERE session_id = NEW.session_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attiva trigger quando si inserisce un evento
CREATE TRIGGER trigger_update_session_activity
    AFTER INSERT ON session_events
    FOR EACH ROW
    EXECUTE FUNCTION update_session_activity();

COMMENT ON FUNCTION update_session_activity()
    IS 'Aggiorna automaticamente last_activity quando arriva nuovo evento';

-- =====================================================
-- CLEANUP AUTOMATICO: Cancella sessioni vecchie
-- =====================================================
-- Funzione per pulire sessioni più vecchie di 7 giorni
-- (evita che il database cresca all'infinito)

CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Cancella sessioni non attive da più di 7 giorni
    DELETE FROM user_sessions
    WHERE last_activity < NOW() - INTERVAL '7 days';

    -- Conta quante ne abbiamo cancellate
    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_sessions()
    IS 'Cancella sessioni inattive da più di 7 giorni (restituisce numero cancellate)';

-- =====================================================
-- DATI DI TEST (Opzionale - per verificare che funziona)
-- =====================================================
-- Inserisce 1 sessione di test per vedere che tutto ok

-- Sessione di test per user "test-user"
INSERT INTO user_sessions (user_id, session_id, phase, progress)
VALUES (
    'test-user-1',
    gen_random_uuid(),
    'risk_assessment',
    42
) ON CONFLICT DO NOTHING;

-- Evento di test: caricamento ATECO
INSERT INTO session_events (user_id, session_id, event_type, event_data)
SELECT
    'test-user-1',
    session_id,
    'ateco_uploaded',
    '{"code": "62.01", "source": "manual", "timestamp": "2025-10-10T14:23:00Z"}'::jsonb
FROM user_sessions
WHERE user_id = 'test-user-1'
LIMIT 1;

-- =====================================================
-- QUERY DI VERIFICA
-- =====================================================
-- Dopo aver eseguito questo script, verifica che tutto sia ok:

-- 1. Controlla che le tabelle esistano
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN ('user_sessions', 'session_events');

-- 2. Controlla che gli indici siano creati
-- SELECT indexname FROM pg_indexes
-- WHERE tablename IN ('user_sessions', 'session_events');

-- 3. Controlla i dati di test
-- SELECT * FROM user_sessions WHERE user_id = 'test-user-1';
-- SELECT * FROM session_events WHERE user_id = 'test-user-1';

-- 4. Test cleanup function (SOLO TEST - non cancella nulla se tutto recente)
-- SELECT cleanup_old_sessions();

-- =====================================================
-- FINE SCRIPT
-- =====================================================
-- ✅ Esegui questo script su Railway PostgreSQL
-- ✅ Verifica che non ci siano errori
-- ✅ Le 6 tabelle esistenti NON vengono toccate
-- ✅ Solo 2 nuove tabelle aggiunte
-- =====================================================
