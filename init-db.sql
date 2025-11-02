-- Script de inicialización de la base de datos
-- Este script se ejecuta automáticamente al crear el contenedor

-- Habilitar extensión PostGIS si no está habilitada
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Crear esquema si es necesario
-- CREATE SCHEMA IF NOT EXISTS public;

-- Nota: Las tablas se crearán automáticamente por SQLAlchemy
-- Este archivo es opcional y puede contener seeds iniciales

\echo 'Base de datos inicializada con PostGIS'
