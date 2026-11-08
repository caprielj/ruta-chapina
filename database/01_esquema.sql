-- =====================================================================
-- RUTA CHAPINA - Script 1: esquema de la base de datos (PostgreSQL / Supabase)
-- Ejecutar en: Supabase > SQL Editor > New query
-- =====================================================================

-- Extensión pgvector: permite guardar embeddings y buscar por similitud (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- Solo durante desarrollo: permite volver a ejecutar este script desde cero.
-- (CUIDADO: borra todos los datos. No ejecutar en la demo final)
DROP TABLE IF EXISTS resultados_agentes CASCADE;
DROP TABLE IF EXISTS consumo_tokens     CASCADE;
DROP TABLE IF EXISTS mensajes           CASCADE;
DROP TABLE IF EXISTS conversaciones     CASCADE;
DROP TABLE IF EXISTS documentos_rag     CASCADE;
DROP TABLE IF EXISTS platillos          CASCADE;
DROP TABLE IF EXISTS actividades        CASCADE;
DROP TABLE IF EXISTS destinos           CASCADE;
DROP TABLE IF EXISTS servicios_ia       CASCADE;
DROP TABLE IF EXISTS usuarios           CASCADE;

-- ---------------------------------------------------------------------
-- USUARIOS: login, rol y límite de tokens asignado por el administrador
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id             SERIAL PRIMARY KEY,
    nombre         TEXT        NOT NULL,
    email          TEXT        NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,                 -- contraseña cifrada (nunca en texto plano)
    rol            TEXT        NOT NULL DEFAULT 'usuario'
                   CHECK (rol IN ('admin', 'usuario')),
    activo         BOOLEAN     NOT NULL DEFAULT TRUE,
    limite_tokens  INTEGER     NOT NULL DEFAULT 20000,   -- tope total de tokens del usuario
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- SERVICIOS DE IA: el admin puede activarlos o desactivarlos
-- ---------------------------------------------------------------------
CREATE TABLE servicios_ia (
    id           SERIAL PRIMARY KEY,
    codigo       TEXT    NOT NULL UNIQUE,   -- identificador técnico usado por el backend
    nombre       TEXT    NOT NULL,
    descripcion  TEXT,
    activo       BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- ENTIDADES PROPIAS: destinos, actividades y platillos (CRUD del admin)
-- ---------------------------------------------------------------------
CREATE TABLE destinos (
    id                SERIAL PRIMARY KEY,
    nombre            TEXT          NOT NULL UNIQUE,
    departamento      TEXT          NOT NULL,
    region            TEXT          NOT NULL,
    categoria         TEXT          NOT NULL,   -- cultural, naturaleza, aventura, arqueología...
    descripcion       TEXT          NOT NULL,
    latitud           NUMERIC(9,6)  NOT NULL,   -- para el mapa y el cálculo de distancias
    longitud          NUMERIC(9,6)  NOT NULL,
    costo_diario_gtq  INTEGER       NOT NULL,   -- gasto diario aproximado por persona
    mejor_epoca       TEXT,
    imagen_url        TEXT,
    activo            BOOLEAN       NOT NULL DEFAULT TRUE
);

CREATE TABLE actividades (
    id              SERIAL PRIMARY KEY,
    destino_id      INTEGER       NOT NULL REFERENCES destinos(id) ON DELETE CASCADE,
    nombre          TEXT          NOT NULL,
    tipo            TEXT          NOT NULL,
    descripcion     TEXT          NOT NULL,
    duracion_horas  NUMERIC(5,1)  NOT NULL,
    costo_gtq       INTEGER       NOT NULL DEFAULT 0,
    activo          BOOLEAN       NOT NULL DEFAULT TRUE
);

CREATE TABLE platillos (
    id                  SERIAL PRIMARY KEY,
    nombre              TEXT    NOT NULL UNIQUE,
    tipo                TEXT    NOT NULL,       -- plato fuerte, bebida, postre, antojito
    departamento_origen TEXT    NOT NULL,       -- 'Nacional' si se come en todo el país
    region              TEXT    NOT NULL,
    descripcion         TEXT    NOT NULL,
    ingredientes        TEXT    NOT NULL,
    vegetariano         BOOLEAN NOT NULL DEFAULT FALSE,
    activo              BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- DOCUMENTOS RAG: fragmentos de texto + su embedding para búsqueda semántica.
-- Se llena en la Fase 3 con un script que recorre destinos/actividades/platillos.
-- vector(384): dimensión compatible con los modelos de embeddings que usaremos.
-- ---------------------------------------------------------------------
CREATE TABLE documentos_rag (
    id            BIGSERIAL PRIMARY KEY,
    fuente_tabla  TEXT        NOT NULL,      -- 'destinos' | 'actividades' | 'platillos'
    fuente_id     INTEGER     NOT NULL,      -- id dentro de esa tabla (sirve para citar la fuente)
    titulo        TEXT        NOT NULL,
    contenido     TEXT        NOT NULL,
    embedding     vector(384),
    UNIQUE (fuente_tabla, fuente_id)
);

-- ---------------------------------------------------------------------
-- HISTORIAL: conversaciones y mensajes (se guardan automáticamente)
-- ---------------------------------------------------------------------
CREATE TABLE conversaciones (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER     NOT NULL REFERENCES usuarios(id)     ON DELETE CASCADE,
    servicio_id INTEGER     NOT NULL REFERENCES servicios_ia(id),
    titulo      TEXT        NOT NULL DEFAULT 'Nueva conversación',
    creada_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mensajes (
    id               BIGSERIAL PRIMARY KEY,
    conversacion_id  INTEGER     NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    rol              TEXT        NOT NULL CHECK (rol IN ('user', 'assistant')),
    contenido        TEXT        NOT NULL,
    fuentes          JSONB,                  -- fuentes citadas por el chatbot (tabla + id + título)
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- CONSUMO DE TOKENS: una fila por cada ejecución de un servicio de IA.
-- De aquí salen el reporte web, el bloqueo por límite y el reporte de Power BI.
-- ---------------------------------------------------------------------
CREATE TABLE consumo_tokens (
    id               BIGSERIAL PRIMARY KEY,
    usuario_id       INTEGER     NOT NULL REFERENCES usuarios(id)     ON DELETE CASCADE,
    servicio_id      INTEGER     NOT NULL REFERENCES servicios_ia(id),
    conversacion_id  INTEGER     REFERENCES conversaciones(id) ON DELETE SET NULL,
    tokens_entrada   INTEGER     NOT NULL DEFAULT 0,
    tokens_salida    INTEGER     NOT NULL DEFAULT 0,
    -- columna calculada automáticamente: entrada + salida
    tokens_total     INTEGER GENERATED ALWAYS AS (tokens_entrada + tokens_salida) STORED,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- RESULTADOS DE AGENTES: pasos y resultado final, para mostrarlos en la web
-- ---------------------------------------------------------------------
CREATE TABLE resultados_agentes (
    id           BIGSERIAL PRIMARY KEY,
    usuario_id   INTEGER     NOT NULL REFERENCES usuarios(id)     ON DELETE CASCADE,
    servicio_id  INTEGER     NOT NULL REFERENCES servicios_ia(id),
    solicitud    TEXT        NOT NULL,
    pasos        JSONB       NOT NULL DEFAULT '[]'::jsonb,   -- herramientas usadas, en orden
    resultado    JSONB,                                      -- respuesta final estructurada
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices para que los reportes filtrados por usuario/fecha/servicio sean rápidos
CREATE INDEX idx_consumo_usuario_fecha  ON consumo_tokens (usuario_id, creado_en);
CREATE INDEX idx_consumo_servicio_fecha ON consumo_tokens (servicio_id, creado_en);
CREATE INDEX idx_mensajes_conversacion  ON mensajes (conversacion_id, creado_en);
CREATE INDEX idx_conversaciones_usuario ON conversaciones (usuario_id, creada_en);
CREATE INDEX idx_actividades_destino    ON actividades (destino_id);
