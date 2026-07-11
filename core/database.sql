-- Habilitar extensión para UUID (si no está activa)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Crear tabla de equipos (teams)
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_title VARCHAR(255) DEFAULT 'Sistema de gestión de equipos',
    project_description TEXT DEFAULT 'Herramienta colaborativa para conectar estudiantes y optimizar la asignación de proyectos académicos.',
    max_members INT DEFAULT 3,
    admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Crear tabla de usuarios (users)
-- (Esta definición incluye los campos requeridos y el enlace al equipo)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    profile_picture TEXT,
    roleId INT DEFAULT 1,
    google_refresh_token TEXT,
    google_access_token TEXT,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    bio TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- NOTA: Si tu tabla 'users' ya existe en tu base de datos local, 
-- puedes ejecutar el siguiente ALTER TABLE en lugar de recrearla:
--
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE SET NULL;
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT '';
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;

-- 3. Enlaces de redes sociales de equipos (team_social_links)
CREATE TABLE IF NOT EXISTS team_social_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    platform VARCHAR(100) NOT NULL, -- Ej: Discord, WhatsApp, GitHub
    url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Solicitudes de integración / invitaciones (team_requests)
CREATE TABLE IF NOT EXISTS team_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state VARCHAR(50) DEFAULT 'PENDIENTE' CHECK (state IN ('PENDIENTE', 'ACEPTADA', 'RECHAZADA', 'CANCELADA')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
