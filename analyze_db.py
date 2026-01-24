import asyncio
import asyncpg

async def analyze_db():
    conn = await asyncpg.connect('postgresql://postgres:HANNIEL@localhost:5433/novaguardian')
    
    print('=== ESTRUCTURA DE TABLAS ===')
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    for t in tables:
        print(f'  - {t["table_name"]}')
    
    print('\n=== PERSONAS MONITOREADAS ===')
    persons = await conn.fetch('SELECT id, first_name, last_name FROM monitored_persons')
    for p in persons:
        print(f'  ID: {p["id"]} - {p["first_name"]} {p["last_name"]}')
    
    print('\n=== DISPOSITIVOS ===')
    devices = await conn.fetch('SELECT id, name, monitored_person_id FROM devices')
    for d in devices:
        print(f'  Device ID: {d["id"]}')
        print(f'  Person ID: {d["monitored_person_id"]}')
    
    print('\n=== ALERTAS (estado de lectura) ===')
    alerts = await conn.fetch('SELECT id, title, is_read, severity FROM alerts LIMIT 5')
    for a in alerts:
        print(f'  {a["title"][:30]}... - Read: {a["is_read"]} - {a["severity"]}')
    
    print('\n=== COLUMNAS DE ALERTS ===')
    cols = await conn.fetch("""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_name = 'alerts' ORDER BY ordinal_position
    """)
    for c in cols:
        print(f'  {c["column_name"]}: {c["data_type"]}')
    
    print('\n=== MEDICAMENTOS ===')
    meds = await conn.fetch('SELECT * FROM medications LIMIT 3')
    print(f'  Total: {len(meds)}')
    
    print('\n=== COLUMNAS DE MEDICATIONS ===')
    cols = await conn.fetch("""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_name = 'medications' ORDER BY ordinal_position
    """)
    for c in cols:
        print(f'  {c["column_name"]}: {c["data_type"]}')
    
    print('\n=== CONTACTOS DE EMERGENCIA ===')
    contacts = await conn.fetch('SELECT * FROM emergency_contacts LIMIT 5')
    for c in contacts:
        print(f'  {c["name"]} - {c["phone"]} - Person: {c["monitored_person_id"]}')
    
    print('\n=== CONDICIONES MÉDICAS ===')
    conds = await conn.fetch('SELECT * FROM medical_conditions LIMIT 5')
    print(f'  Total: {len(conds)}')
    
    await conn.close()

asyncio.run(analyze_db())
