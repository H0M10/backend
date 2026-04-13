import asyncio, asyncpg
async def main():
    conn = await asyncpg.connect('postgresql://postgres:HANNIEL@localhost:5433/novaguardian')
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'password_reset_tokens'")
    print([r[0] for r in rows])
    await conn.close()
asyncio.run(main())