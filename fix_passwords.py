import bcrypt
import asyncio
import asyncpg

passwords = {
    'hanniel@novaguardian.online': 'Test123456',
    'ian@novaguardian.online': 'Rddf5782',
    'fernando@novaguardian.online': 'BsjQ5136',
    'bryan@novaguardian.online': 'WEDw6978',
    'daniela@novaguardian.online': 'ymez6926'
}

async def update_passwords():
    conn = await asyncpg.connect(
        user='postgres',
        password='HANNIEL',
        database='novaguardian',
        host='localhost',
        port=5433
    )
    
    for email, pwd in passwords.items():
        hash_bytes = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(rounds=12))
        hash_str = hash_bytes.decode('utf-8')
        print(f"Updating {email}: {hash_str[:30]}...")
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE email = $2",
            hash_str, email
        )
    
    # Verificar
    rows = await conn.fetch("SELECT email, password_hash FROM users")
    print("\nVerificacion:")
    for row in rows:
        print(f"  {row['email']}: {row['password_hash'][:30]}...")
    
    await conn.close()
    print("\nPasswords actualizados correctamente!")

asyncio.run(update_passwords())
