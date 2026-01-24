import asyncio
import asyncpg

async def check_users():
    conn = await asyncpg.connect('postgresql://postgres:HANNIEL@localhost:5433/novaguardian')
    users = await conn.fetch('SELECT id, email, first_name FROM users LIMIT 5')
    print('Usuarios en la base de datos:')
    for u in users:
        print(f"  - {u['email']} ({u['first_name']})")
    await conn.close()

asyncio.run(check_users())
