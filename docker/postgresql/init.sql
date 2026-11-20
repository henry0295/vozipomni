-- Inicialización de la base de datos VoziPOmni

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Configuración de timezone
SET timezone = 'America/Bogota';

-- Crear esquemas adicionales si son necesarios
CREATE SCHEMA IF NOT EXISTS reports;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grants (usa los nombres definidos en POSTGRES_DB y POSTGRES_USER del .env)
-- El contenedor postgres ya crea la BD y el usuario con las variables de entorno
-- Aquí solo otorgamos permisos adicionales sobre esquemas
GRANT ALL ON SCHEMA public TO vozipomni_user;
GRANT ALL ON SCHEMA reports TO vozipomni_user;
GRANT ALL ON SCHEMA analytics TO vozipomni_user;
