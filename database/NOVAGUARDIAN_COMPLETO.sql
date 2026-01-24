-- ============================================================================
-- NOVAGUARDIAN - SCRIPT COMPLETO DE BASE DE DATOS
-- Version: 2.0 FINAL
-- Fecha: Enero 2026
-- 
-- INSTRUCCIONES:
-- 1. Conectar a PostgreSQL (puerto 5433, password: HANNIEL)
-- 2. Crear base de datos: CREATE DATABASE novaguardian;
-- 3. Conectar a novaguardian y ejecutar este script completo
-- ============================================================================

-- ============================================================================
-- EXTENSIONES REQUERIDAS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- ELIMINAR TIPOS Y TABLAS EXISTENTES (ORDEN CORRECTO POR DEPENDENCIAS)
-- ============================================================================
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS push_tokens CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS vital_signs CASCADE;
DROP TABLE IF EXISTS geofences CASCADE;
DROP TABLE IF EXISTS medications CASCADE;
DROP TABLE IF EXISTS medical_conditions CASCADE;
DROP TABLE IF EXISTS emergency_contacts CASCADE;
DROP TABLE IF EXISTS devices CASCADE;
DROP TABLE IF EXISTS monitored_persons CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS notification_status CASCADE;
DROP TYPE IF EXISTS notification_type CASCADE;
DROP TYPE IF EXISTS alert_severity CASCADE;
DROP TYPE IF EXISTS alert_type CASCADE;
DROP TYPE IF EXISTS severity_level CASCADE;
DROP TYPE IF EXISTS condition_type CASCADE;
DROP TYPE IF EXISTS blood_type CASCADE;
DROP TYPE IF EXISTS gender_type CASCADE;
DROP TYPE IF EXISTS device_model CASCADE;
DROP TYPE IF EXISTS device_status CASCADE;

-- ============================================================================
-- TIPOS ENUMERADOS (ENUMS)
-- ============================================================================

-- Estado del dispositivo
CREATE TYPE device_status AS ENUM (
    'connected',
    'disconnected', 
    'low_battery',
    'error',
    'charging'
);

-- Modelo del dispositivo
CREATE TYPE device_model AS ENUM (
    'NovaBand V1',
    'NovaBand V2',
    'NovaBand Pro'
);

-- Genero
CREATE TYPE gender_type AS ENUM (
    'male',
    'female',
    'other'
);

-- Tipo de sangre
CREATE TYPE blood_type AS ENUM (
    'A+', 'A-',
    'B+', 'B-',
    'AB+', 'AB-',
    'O+', 'O-'
);

-- Tipo de condicion medica
CREATE TYPE condition_type AS ENUM (
    'disease',
    'allergy',
    'medication',
    'surgery',
    'other'
);

-- Nivel de severidad
CREATE TYPE severity_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

-- Tipo de alerta
CREATE TYPE alert_type AS ENUM (
    'HIGH_HEART_RATE',
    'LOW_HEART_RATE',
    'LOW_SPO2',
    'HIGH_TEMPERATURE',
    'LOW_TEMPERATURE',
    'HIGH_BLOOD_PRESSURE',
    'LOW_BLOOD_PRESSURE',
    'FALL_DETECTED',
    'SOS_BUTTON',
    'GEOFENCE_EXIT',
    'GEOFENCE_ENTER',
    'LOW_BATTERY',
    'DEVICE_DISCONNECTED',
    'DEVICE_ERROR'
);

-- Severidad de alerta
CREATE TYPE alert_severity AS ENUM (
    'info',
    'warning',
    'critical'
);

-- Tipo de notificacion
CREATE TYPE notification_type AS ENUM (
    'push',
    'sms',
    'email',
    'whatsapp'
);

-- Estado de notificacion
CREATE TYPE notification_status AS ENUM (
    'pending',
    'sent',
    'failed',
    'read'
);

-- ============================================================================
-- TABLA: users (Usuarios/Cuidadores)
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    photo_url TEXT,
    
    -- Estado de cuenta
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Tokens de verificacion
    verification_token VARCHAR(255),
    verification_token_expires TIMESTAMPTZ,
    reset_password_token VARCHAR(255),
    reset_password_token_expires TIMESTAMPTZ,
    
    -- Actividad
    last_login TIMESTAMPTZ,
    
    -- Preferencias
    language VARCHAR(10) NOT NULL DEFAULT 'es',
    timezone VARCHAR(50) NOT NULL DEFAULT 'America/Mexico_City',
    
    -- Configuracion de notificaciones
    push_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    email_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sms_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    whatsapp_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: monitored_persons (Adultos Mayores Monitoreados)
-- ============================================================================
CREATE TABLE monitored_persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Datos personales
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE,
    gender gender_type,
    photo_url TEXT,
    
    -- Datos medicos
    blood_type blood_type,
    weight DECIMAL(5,2),
    height DECIMAL(5,2),
    notes TEXT,
    
    -- Relacion con el cuidador
    relationship VARCHAR(50),
    
    -- Umbrales de signos vitales (personalizados)
    heart_rate_min DECIMAL(5,2) NOT NULL DEFAULT 50,
    heart_rate_max DECIMAL(5,2) NOT NULL DEFAULT 120,
    spo2_min DECIMAL(5,2) NOT NULL DEFAULT 92,
    temperature_min DECIMAL(4,2) NOT NULL DEFAULT 35.0,
    temperature_max DECIMAL(4,2) NOT NULL DEFAULT 38.5,
    systolic_bp_min DECIMAL(5,2) NOT NULL DEFAULT 90,
    systolic_bp_max DECIMAL(5,2) NOT NULL DEFAULT 140,
    diastolic_bp_min DECIMAL(5,2) NOT NULL DEFAULT 60,
    diastolic_bp_max DECIMAL(5,2) NOT NULL DEFAULT 90,
    
    -- Estado
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: devices (Dispositivos IoT - Pulseras)
-- ============================================================================
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identificadores unicos
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    mac_address VARCHAR(17) UNIQUE,
    
    -- Informacion del dispositivo
    name VARCHAR(100),
    model device_model NOT NULL DEFAULT 'NovaBand V1',
    firmware_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    hardware_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    
    -- Vinculacion (puede estar sin asignar)
    monitored_person_id UUID REFERENCES monitored_persons(id) ON DELETE SET NULL,
    
    -- Estado actual
    status device_status NOT NULL DEFAULT 'disconnected',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    battery_level DECIMAL(5,2) NOT NULL DEFAULT 100,
    is_charging BOOLEAN NOT NULL DEFAULT FALSE,
    is_connected BOOLEAN NOT NULL DEFAULT FALSE,
    signal_strength DECIMAL(5,2),
    
    -- Timestamps de actividad
    last_seen TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    linked_at TIMESTAMPTZ,
    
    -- Configuracion
    sync_interval_seconds DECIMAL(6,2) NOT NULL DEFAULT 30,
    heart_rate_sensor_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    spo2_sensor_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    temperature_sensor_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    gps_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    fall_detection_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: vital_signs (Signos Vitales)
-- ============================================================================
CREATE TABLE vital_signs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    
    -- Signos vitales
    heart_rate DECIMAL(5,2),
    spo2 DECIMAL(5,2),
    temperature DECIMAL(4,2),
    systolic_bp DECIMAL(5,2),
    diastolic_bp DECIMAL(5,2),
    
    -- Actividad
    steps INTEGER NOT NULL DEFAULT 0,
    calories DECIMAL(7,2) NOT NULL DEFAULT 0,
    distance DECIMAL(10,2) NOT NULL DEFAULT 0,
    
    -- Calidad de lectura
    heart_rate_quality DECIMAL(5,2),
    spo2_quality DECIMAL(5,2),
    
    -- Timestamp de lectura
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: locations (Ubicaciones GPS)
-- ============================================================================
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    
    -- Coordenadas
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    altitude DECIMAL(10,2),
    accuracy DECIMAL(6,2),
    speed DECIMAL(6,2),
    heading DECIMAL(5,2),
    
    -- Direccion (geocodificacion inversa)
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    
    -- Timestamp
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: geofences (Zonas Seguras)
-- ============================================================================
CREATE TABLE geofences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitored_person_id UUID NOT NULL REFERENCES monitored_persons(id) ON DELETE CASCADE,
    
    -- Configuracion de zona
    name VARCHAR(100) NOT NULL,
    description TEXT,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    radius DECIMAL(10,2) NOT NULL DEFAULT 100,
    address TEXT,
    
    -- Configuracion de alertas
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notify_on_exit BOOLEAN NOT NULL DEFAULT TRUE,
    notify_on_enter BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Visualizacion
    color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: medical_conditions (Condiciones Medicas)
-- ============================================================================
CREATE TABLE medical_conditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitored_person_id UUID NOT NULL REFERENCES monitored_persons(id) ON DELETE CASCADE,
    
    -- Datos de la condicion
    condition_type condition_type NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    severity severity_level NOT NULL DEFAULT 'medium',
    diagnosis_date DATE,
    notes TEXT,
    
    -- Estado
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: medications (Medicamentos)
-- ============================================================================
CREATE TABLE medications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitored_person_id UUID NOT NULL REFERENCES monitored_persons(id) ON DELETE CASCADE,
    
    -- Datos del medicamento
    name VARCHAR(200) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    start_date DATE,
    end_date DATE,
    notes TEXT,
    
    -- Estado
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: emergency_contacts (Contactos de Emergencia)
-- ============================================================================
CREATE TABLE emergency_contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitored_person_id UUID NOT NULL REFERENCES monitored_persons(id) ON DELETE CASCADE,
    
    -- Datos del contacto
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    relationship VARCHAR(50),
    
    -- Configuracion
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    notify_on_alerts BOOLEAN NOT NULL DEFAULT TRUE,
    notify_critical_only BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Notas
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: alerts (Alertas)
-- ============================================================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    
    -- Tipo y severidad
    alert_type alert_type NOT NULL,
    severity alert_severity NOT NULL,
    
    -- Contenido
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    
    -- Valor que disparo la alerta
    value DECIMAL(10,2),
    
    -- Ubicacion donde ocurrio
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    address TEXT,
    
    -- Estados
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id),
    
    -- Falsa alarma
    is_false_alarm BOOLEAN NOT NULL DEFAULT FALSE,
    false_alarm_notes TEXT,
    
    -- Datos adicionales (JSON)
    data JSONB,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: notifications (Notificaciones Enviadas)
-- ============================================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_id UUID REFERENCES alerts(id) ON DELETE SET NULL,
    
    -- Contenido
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    
    -- Tipo y estado
    type notification_type NOT NULL,
    status notification_status NOT NULL DEFAULT 'pending',
    
    -- Timestamps de envio/lectura
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    
    -- Datos adicionales
    data JSONB,
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLA: push_tokens (Tokens de Notificaciones Push)
-- ============================================================================
CREATE TABLE push_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Token
    token TEXT NOT NULL,
    platform VARCHAR(20) NOT NULL,
    device_name VARCHAR(100),
    
    -- Estado
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Evitar duplicados
    UNIQUE(user_id, token)
);

-- ============================================================================
-- TABLA: refresh_tokens (Tokens de Sesion)
-- ============================================================================
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Token
    token VARCHAR(500) UNIQUE NOT NULL,
    
    -- Info del dispositivo
    device_info TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Expiracion
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Revocacion
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDICES PARA OPTIMIZACION
-- ============================================================================

-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Monitored Persons
CREATE INDEX idx_monitored_persons_user_id ON monitored_persons(user_id);
CREATE INDEX idx_monitored_persons_is_active ON monitored_persons(is_active);

-- Devices
CREATE INDEX idx_devices_monitored_person_id ON devices(monitored_person_id);
CREATE INDEX idx_devices_serial_number ON devices(serial_number);
CREATE INDEX idx_devices_code ON devices(code);
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_is_connected ON devices(is_connected);

-- Vital Signs
CREATE INDEX idx_vital_signs_device_id ON vital_signs(device_id);
CREATE INDEX idx_vital_signs_recorded_at ON vital_signs(recorded_at DESC);
CREATE INDEX idx_vital_signs_device_recorded ON vital_signs(device_id, recorded_at DESC);

-- Locations
CREATE INDEX idx_locations_device_id ON locations(device_id);
CREATE INDEX idx_locations_recorded_at ON locations(recorded_at DESC);
CREATE INDEX idx_locations_device_recorded ON locations(device_id, recorded_at DESC);

-- Geofences
CREATE INDEX idx_geofences_monitored_person_id ON geofences(monitored_person_id);
CREATE INDEX idx_geofences_is_active ON geofences(is_active);

-- Medical Conditions
CREATE INDEX idx_medical_conditions_monitored_person_id ON medical_conditions(monitored_person_id);
CREATE INDEX idx_medical_conditions_is_active ON medical_conditions(is_active);

-- Medications
CREATE INDEX idx_medications_monitored_person_id ON medications(monitored_person_id);
CREATE INDEX idx_medications_is_active ON medications(is_active);

-- Emergency Contacts
CREATE INDEX idx_emergency_contacts_monitored_person_id ON emergency_contacts(monitored_person_id);
CREATE INDEX idx_emergency_contacts_is_primary ON emergency_contacts(is_primary);

-- Alerts
CREATE INDEX idx_alerts_device_id ON alerts(device_id);
CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX idx_alerts_is_read ON alerts(is_read);
CREATE INDEX idx_alerts_is_resolved ON alerts(is_resolved);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_unread ON alerts(is_read) WHERE is_read = FALSE;

-- Notifications
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- Push Tokens
CREATE INDEX idx_push_tokens_user_id ON push_tokens(user_id);
CREATE INDEX idx_push_tokens_is_active ON push_tokens(is_active);

-- Refresh Tokens
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================================================
-- TRIGGERS PARA ACTUALIZAR updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a todas las tablas con updated_at
CREATE TRIGGER trigger_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_monitored_persons_updated_at 
    BEFORE UPDATE ON monitored_persons 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_devices_updated_at 
    BEFORE UPDATE ON devices 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_geofences_updated_at 
    BEFORE UPDATE ON geofences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_medical_conditions_updated_at 
    BEFORE UPDATE ON medical_conditions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_medications_updated_at 
    BEFORE UPDATE ON medications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_emergency_contacts_updated_at 
    BEFORE UPDATE ON emergency_contacts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_alerts_updated_at 
    BEFORE UPDATE ON alerts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_push_tokens_updated_at 
    BEFORE UPDATE ON push_tokens 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DATOS DE PRUEBA
-- ============================================================================

/*
 CREDENCIALES DE ACCESO:
 ========================
 | Email                          | Password     |
 |--------------------------------|--------------|
 | hanniel@novaguardian.online    | Test123456   |
 | ian@novaguardian.online        | Rddf5782     |
 | fernando@novaguardian.online   | BsjQ5136     |
 | bryan@novaguardian.online      | WEDw6978     |
 | daniela@novaguardian.online    | ymez6926     |
 ========================
*/

-- USUARIOS
INSERT INTO users (id, email, password_hash, first_name, last_name, phone, is_active, is_verified, whatsapp_notifications_enabled) VALUES
('11111111-1111-1111-1111-111111111111', 'hanniel@novaguardian.online', 
 crypt('Test123456', gen_salt('bf', 12)), 'Hanniel', 'Admin', '+5215512345678', true, true, true),
('22222222-2222-2222-2222-222222222222', 'ian@novaguardian.online', 
 crypt('Rddf5782', gen_salt('bf', 12)), 'Ian', 'Garcia', '+5215512345679', true, true, true),
('33333333-3333-3333-3333-333333333333', 'fernando@novaguardian.online', 
 crypt('BsjQ5136', gen_salt('bf', 12)), 'Fernando', 'Lopez', '+5215512345680', true, true, false),
('44444444-4444-4444-4444-444444444444', 'bryan@novaguardian.online', 
 crypt('WEDw6978', gen_salt('bf', 12)), 'Bryan', 'Martinez', '+5215512345681', true, true, false),
('55555555-5555-5555-5555-555555555555', 'daniela@novaguardian.online', 
 crypt('ymez6926', gen_salt('bf', 12)), 'Daniela', 'Hernandez', '+5215512345682', true, true, true);

-- PERSONAS MONITOREADAS
INSERT INTO monitored_persons (id, user_id, first_name, last_name, birth_date, gender, blood_type, weight, height, relationship, notes) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 
 'Maria', 'Gonzalez', '1945-03-15', 'female', 'O+', 65.5, 155, 'grandmother', 'Abuela materna, vive sola'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', 
 'Roberto', 'Sanchez', '1940-07-22', 'male', 'A+', 78.0, 170, 'grandfather', 'Abuelo paterno'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', '33333333-3333-3333-3333-333333333333', 
 'Carmen', 'Rodriguez', '1950-11-08', 'female', 'B+', 70.0, 160, 'mother', 'Madre, tiene artritis'),
('dddddddd-dddd-dddd-dddd-dddddddddddd', '44444444-4444-4444-4444-444444444444', 
 'Jose', 'Perez', '1948-05-30', 'male', 'AB+', 82.0, 175, 'father', 'Padre, problemas respiratorios'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '55555555-5555-5555-5555-555555555555', 
 'Rosa', 'Mendoza', '1942-09-12', 'female', 'O-', 58.0, 150, 'grandmother', 'Abuela, Alzheimer leve');

-- DISPOSITIVOS
INSERT INTO devices (id, monitored_person_id, serial_number, code, mac_address, name, status, battery_level, is_connected, last_seen, linked_at) VALUES
('d1111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
 'NV-2026-001', 'NOVA001', 'AA:BB:CC:DD:EE:01', 'Pulsera Maria', 'connected', 85, true, NOW(), NOW()),
('d2222222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 
 'NV-2026-002', 'NOVA002', 'AA:BB:CC:DD:EE:02', 'Pulsera Roberto', 'connected', 72, true, NOW(), NOW()),
('d3333333-3333-3333-3333-333333333333', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 
 'NV-2026-003', 'NOVA003', 'AA:BB:CC:DD:EE:03', 'Pulsera Carmen', 'connected', 90, true, NOW(), NOW()),
('d4444444-4444-4444-4444-444444444444', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 
 'NV-2026-004', 'NOVA004', 'AA:BB:CC:DD:EE:04', 'Pulsera Jose', 'low_battery', 25, true, NOW(), NOW()),
('d5555555-5555-5555-5555-555555555555', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 
 'NV-2026-005', 'NOVA005', 'AA:BB:CC:DD:EE:05', 'Pulsera Rosa', 'connected', 95, true, NOW(), NOW());

-- CONDICIONES MEDICAS
INSERT INTO medical_conditions (monitored_person_id, condition_type, name, description, severity) VALUES
-- Maria
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'disease', 'Diabetes Tipo 2', 'Controlada con metformina 850mg', 'medium'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'disease', 'Hipertension', 'Presion arterial alta, toma losartan', 'medium'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'allergy', 'Alergia a Sulfas', 'Reaccion cutanea severa', 'high'),
-- Roberto
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'disease', 'Artritis Reumatoide', 'Artritis en manos y rodillas', 'medium'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'allergy', 'Alergia a Penicilina', 'Reaccion anafilactica', 'critical'),
-- Carmen
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'disease', 'Osteoporosis', 'Densidad osea baja, riesgo de fracturas', 'medium'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'disease', 'Hipotiroidismo', 'Tiroides baja, toma levotiroxina', 'low'),
-- Jose
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'disease', 'EPOC', 'Enfermedad pulmonar obstructiva cronica', 'high'),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'disease', 'Insuficiencia Cardiaca', 'Clase funcional II', 'high'),
-- Rosa
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'disease', 'Alzheimer', 'Etapa inicial, perdida de memoria reciente', 'high'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'disease', 'Osteoartritis', 'Desgaste en rodillas', 'medium');

-- MEDICAMENTOS
INSERT INTO medications (monitored_person_id, name, dosage, frequency, is_active) VALUES
-- Maria
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Metformina', '850mg', 'Dos veces al dia', true),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Losartan', '50mg', 'Una vez al dia', true),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Aspirina', '100mg', 'Una vez al dia', true),
-- Roberto
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Metotrexato', '15mg', 'Una vez por semana', true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Acido Folico', '5mg', 'Diario excepto dia de metotrexato', true),
-- Carmen
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Levotiroxina', '100mcg', 'En ayunas', true),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Calcio + Vitamina D', '600mg/400UI', 'Dos veces al dia', true),
-- Jose
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Salbutamol Inhalador', '100mcg', 'Cada 6 horas PRN', true),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Furosemida', '40mg', 'Una vez al dia', true),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Warfarina', '5mg', 'Una vez al dia', true),
-- Rosa
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Donepezilo', '10mg', 'Una vez al dia por la noche', true),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Memantina', '10mg', 'Dos veces al dia', true);

-- CONTACTOS DE EMERGENCIA
INSERT INTO emergency_contacts (monitored_person_id, name, phone, email, relationship, is_primary, notify_on_alerts) VALUES
-- Maria
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Hanniel Admin', '+5215512345678', 'hanniel@novaguardian.online', 'Nieto', true, true),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Dr. Carlos Ramirez', '+5215500001111', 'dr.ramirez@hospital.com', 'Medico de cabecera', false, true),
-- Roberto
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Ian Garcia', '+5215512345679', 'ian@novaguardian.online', 'Nieto', true, true),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Lucia Sanchez', '+5215500002222', null, 'Hija', false, true),
-- Carmen
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Fernando Lopez', '+5215512345680', 'fernando@novaguardian.online', 'Hijo', true, true),
-- Jose
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Bryan Martinez', '+5215512345681', 'bryan@novaguardian.online', 'Hijo', true, true),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Dr. Ana Gomez', '+5215500003333', 'dra.gomez@cardio.com', 'Cardiologa', false, true),
-- Rosa
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Daniela Hernandez', '+5215512345682', 'daniela@novaguardian.online', 'Nieta', true, true),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Centro de Dia Los Olivos', '+5215500004444', null, 'Centro de atencion', false, false);

-- ZONAS SEGURAS (GEOFENCES)
INSERT INTO geofences (monitored_person_id, name, description, latitude, longitude, radius, address, notify_on_exit, notify_on_enter, color) VALUES
-- Maria (CDMX - Coyoacan)
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Casa', 'Domicilio principal', 19.3500, -99.1620, 100, 'Col. Coyoacan, CDMX', true, false, '#10B981'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Parque Coyoacan', 'Parque donde camina', 19.3520, -99.1600, 200, 'Parque de Coyoacan, CDMX', true, false, '#3B82F6'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Farmacia', 'Farmacia del ahorro cercana', 19.3510, -99.1650, 50, 'Av. Mexico, Coyoacan', false, false, '#8B5CF6'),
-- Roberto (CDMX - Roma Norte)
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Casa', 'Departamento', 19.4195, -99.1580, 100, 'Col. Roma Norte, CDMX', true, false, '#10B981'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Clinica', 'Clinica de rehabilitacion', 19.4210, -99.1550, 150, 'Av. Insurgentes, CDMX', true, false, '#EF4444'),
-- Carmen (Guadalajara)
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Casa', 'Casa familiar', 20.6767, -103.3475, 150, 'Col. Providencia, GDL', true, false, '#10B981'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Mercado', 'Mercado donde compra', 20.6780, -103.3450, 100, 'Mercado Providencia, GDL', true, false, '#F59E0B'),
-- Jose (Monterrey)
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Casa', 'Casa con jardin', 25.6866, -100.3161, 120, 'Col. Del Valle, MTY', true, false, '#10B981'),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'Hospital', 'Hospital Universitario', 25.6900, -100.3100, 300, 'Av. Gonzalitos, MTY', true, true, '#EF4444'),
-- Rosa (Puebla)
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Casa', 'Casa del centro', 19.0414, -98.2063, 80, 'Centro Historico, Puebla', true, false, '#10B981'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Centro de Dia', 'Centro de atencion diurna', 19.0430, -98.2040, 100, 'Calle 5 de Mayo, Puebla', true, true, '#3B82F6');

-- SIGNOS VITALES (Ultimas lecturas - Simulando datos reales)
INSERT INTO vital_signs (device_id, heart_rate, spo2, temperature, systolic_bp, diastolic_bp, steps, calories, recorded_at) VALUES
-- Maria - Lecturas normales
('d1111111-1111-1111-1111-111111111111', 72, 97, 36.5, 125, 80, 150, 45.5, NOW() - interval '5 minutes'),
('d1111111-1111-1111-1111-111111111111', 75, 96, 36.6, 128, 82, 180, 52.0, NOW() - interval '35 minutes'),
('d1111111-1111-1111-1111-111111111111', 70, 98, 36.4, 122, 78, 220, 65.0, NOW() - interval '1 hour 5 minutes'),
('d1111111-1111-1111-1111-111111111111', 78, 95, 36.7, 130, 85, 280, 82.0, NOW() - interval '1 hour 35 minutes'),
('d1111111-1111-1111-1111-111111111111', 68, 97, 36.5, 120, 75, 350, 105.0, NOW() - interval '2 hours'),
('d1111111-1111-1111-1111-111111111111', 74, 96, 36.6, 125, 80, 420, 125.0, NOW() - interval '3 hours'),
-- Roberto - Lecturas normales
('d2222222-2222-2222-2222-222222222222', 68, 96, 36.3, 130, 82, 100, 30.0, NOW() - interval '10 minutes'),
('d2222222-2222-2222-2222-222222222222', 70, 97, 36.4, 128, 80, 150, 45.0, NOW() - interval '40 minutes'),
('d2222222-2222-2222-2222-222222222222', 65, 98, 36.2, 125, 78, 200, 60.0, NOW() - interval '1 hour 10 minutes'),
('d2222222-2222-2222-2222-222222222222', 72, 96, 36.4, 132, 84, 250, 75.0, NOW() - interval '2 hours'),
-- Carmen - Lecturas normales
('d3333333-3333-3333-3333-333333333333', 76, 98, 36.6, 118, 75, 200, 60.0, NOW() - interval '15 minutes'),
('d3333333-3333-3333-3333-333333333333', 78, 97, 36.5, 120, 78, 280, 85.0, NOW() - interval '45 minutes'),
('d3333333-3333-3333-3333-333333333333', 74, 99, 36.4, 115, 72, 350, 105.0, NOW() - interval '1 hour 15 minutes'),
('d3333333-3333-3333-3333-333333333333', 80, 96, 36.7, 122, 80, 420, 125.0, NOW() - interval '2 hours'),
-- Jose - Algunas lecturas preocupantes (EPOC + IC)
('d4444444-4444-4444-4444-444444444444', 95, 91, 37.2, 145, 92, 50, 15.0, NOW() - interval '5 minutes'),
('d4444444-4444-4444-4444-444444444444', 88, 93, 37.0, 140, 88, 80, 24.0, NOW() - interval '35 minutes'),
('d4444444-4444-4444-4444-444444444444', 82, 94, 36.8, 138, 85, 100, 30.0, NOW() - interval '1 hour 5 minutes'),
('d4444444-4444-4444-4444-444444444444', 90, 92, 37.1, 142, 90, 120, 36.0, NOW() - interval '2 hours'),
-- Rosa - Lecturas normales
('d5555555-5555-5555-5555-555555555555', 70, 97, 36.4, 120, 75, 120, 35.0, NOW() - interval '20 minutes'),
('d5555555-5555-5555-5555-555555555555', 72, 96, 36.5, 122, 78, 180, 55.0, NOW() - interval '50 minutes'),
('d5555555-5555-5555-5555-555555555555', 68, 98, 36.3, 118, 72, 250, 75.0, NOW() - interval '1 hour 20 minutes'),
('d5555555-5555-5555-5555-555555555555', 74, 97, 36.5, 125, 80, 300, 90.0, NOW() - interval '2 hours');

-- UBICACIONES (Ultimas posiciones)
INSERT INTO locations (device_id, latitude, longitude, accuracy, address, city, state, country, recorded_at) VALUES
('d1111111-1111-1111-1111-111111111111', 19.3500, -99.1620, 10.5, 'Calle Francisco Sosa 123, Col. Coyoacan', 'Ciudad de Mexico', 'CDMX', 'Mexico', NOW() - interval '2 minutes'),
('d2222222-2222-2222-2222-222222222222', 19.4195, -99.1580, 8.2, 'Calle Durango 456, Col. Roma Norte', 'Ciudad de Mexico', 'CDMX', 'Mexico', NOW() - interval '5 minutes'),
('d3333333-3333-3333-3333-333333333333', 20.6767, -103.3475, 12.0, 'Av. Providencia 789, Col. Providencia', 'Guadalajara', 'Jalisco', 'Mexico', NOW() - interval '8 minutes'),
('d4444444-4444-4444-4444-444444444444', 25.6866, -100.3161, 9.5, 'Calle Rio Amazonas 321, Col. Del Valle', 'Monterrey', 'Nuevo Leon', 'Mexico', NOW() - interval '3 minutes'),
('d5555555-5555-5555-5555-555555555555', 19.0414, -98.2063, 11.0, 'Calle 5 de Mayo 654, Centro Historico', 'Puebla', 'Puebla', 'Mexico', NOW() - interval '10 minutes');

-- ALERTAS (Ejemplos de diferentes tipos)
INSERT INTO alerts (device_id, alert_type, severity, title, message, value, latitude, longitude, address, is_read, is_resolved, created_at) VALUES
-- Alertas actuales (no resueltas)
('d4444444-4444-4444-4444-444444444444', 'LOW_BATTERY', 'warning', 
 'Bateria baja', 'La pulsera de Jose tiene solo 25% de bateria. Por favor cargarla pronto.', 
 25, 25.6866, -100.3161, 'Col. Del Valle, MTY', false, false, NOW() - interval '30 minutes'),

('d4444444-4444-4444-4444-444444444444', 'LOW_SPO2', 'critical', 
 'Nivel de oxigeno bajo', 'Jose registro un nivel de oxigeno de 91%. Se recomienda verificar su estado inmediatamente.', 
 91, 25.6866, -100.3161, 'Col. Del Valle, MTY', false, false, NOW() - interval '10 minutes'),

('d4444444-4444-4444-4444-444444444444', 'HIGH_HEART_RATE', 'warning', 
 'Ritmo cardiaco elevado', 'Jose registro 95 BPM, por encima de su limite normal de 90 BPM.', 
 95, 25.6866, -100.3161, 'Col. Del Valle, MTY', false, false, NOW() - interval '5 minutes'),

-- Alertas historicas (ya resueltas/leidas)
('d1111111-1111-1111-1111-111111111111', 'HIGH_HEART_RATE', 'critical', 
 'Frecuencia cardiaca muy elevada', 'Maria registro 125 BPM durante una caminata.', 
 125, 19.3520, -99.1600, 'Parque Coyoacan', true, true, NOW() - interval '2 hours'),

('d5555555-5555-5555-5555-555555555555', 'GEOFENCE_EXIT', 'warning', 
 'Salida de zona segura', 'Rosa salio de la zona "Casa". Ubicacion actual: Centro de Dia.', 
 null, 19.0430, -98.2040, 'Calle 5 de Mayo, Puebla', true, true, NOW() - interval '5 hours'),

('d2222222-2222-2222-2222-222222222222', 'DEVICE_DISCONNECTED', 'warning', 
 'Dispositivo desconectado', 'La pulsera de Roberto perdio conexion por 15 minutos.', 
 null, 19.4195, -99.1580, 'Col. Roma Norte', true, true, NOW() - interval '8 hours'),

('d3333333-3333-3333-3333-333333333333', 'FALL_DETECTED', 'critical', 
 'Posible caida detectada', 'Se detecto un patron de movimiento compatible con una caida. Carmen no confirmo estar bien.', 
 null, 20.6767, -103.3475, 'Col. Providencia, GDL', true, true, NOW() - interval '1 day'),

('d1111111-1111-1111-1111-111111111111', 'LOW_TEMPERATURE', 'warning', 
 'Temperatura baja', 'Maria registro una temperatura de 34.8 C, debajo del umbral de 35 C.', 
 34.8, 19.3500, -99.1620, 'Casa - Coyoacan', true, true, NOW() - interval '2 days');

-- NOTIFICACIONES (Ejemplos enviadas)
INSERT INTO notifications (user_id, alert_id, title, body, type, status, sent_at, created_at) VALUES
('44444444-4444-4444-4444-444444444444', 
 (SELECT id FROM alerts WHERE device_id = 'd4444444-4444-4444-4444-444444444444' AND alert_type = 'LOW_SPO2' LIMIT 1),
 'ALERTA CRITICA: Oxigeno bajo', 
 'Jose registro SpO2 de 91%. Verificar inmediatamente.',
 'push', 'sent', NOW() - interval '9 minutes', NOW() - interval '10 minutes'),

('44444444-4444-4444-4444-444444444444', 
 (SELECT id FROM alerts WHERE device_id = 'd4444444-4444-4444-4444-444444444444' AND alert_type = 'LOW_BATTERY' LIMIT 1),
 'Bateria baja en pulsera', 
 'La pulsera de Jose tiene 25% de bateria.',
 'push', 'sent', NOW() - interval '29 minutes', NOW() - interval '30 minutes');

-- ============================================================================
-- VERIFICACION FINAL
-- ============================================================================
SELECT '========================================' AS info;
SELECT 'NOVAGUARDIAN - BASE DE DATOS CREADA' AS info;
SELECT '========================================' AS info;

SELECT 'Usuarios:' AS tabla, COUNT(*)::text AS registros FROM users
UNION ALL SELECT 'Personas monitoreadas:', COUNT(*)::text FROM monitored_persons
UNION ALL SELECT 'Dispositivos:', COUNT(*)::text FROM devices
UNION ALL SELECT 'Condiciones medicas:', COUNT(*)::text FROM medical_conditions
UNION ALL SELECT 'Medicamentos:', COUNT(*)::text FROM medications
UNION ALL SELECT 'Contactos emergencia:', COUNT(*)::text FROM emergency_contacts
UNION ALL SELECT 'Zonas seguras:', COUNT(*)::text FROM geofences
UNION ALL SELECT 'Signos vitales:', COUNT(*)::text FROM vital_signs
UNION ALL SELECT 'Ubicaciones:', COUNT(*)::text FROM locations
UNION ALL SELECT 'Alertas:', COUNT(*)::text FROM alerts
UNION ALL SELECT 'Notificaciones:', COUNT(*)::text FROM notifications;

SELECT '========================================' AS info;
SELECT 'SCRIPT COMPLETADO EXITOSAMENTE' AS info;
SELECT '========================================' AS info;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
