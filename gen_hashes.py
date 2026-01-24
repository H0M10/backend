import bcrypt

passwords = {
    'hanniel@novaguardian.online': 'Test123456',
    'ian@novaguardian.online': 'Rddf5782',
    'fernando@novaguardian.online': 'BsjQ5136',
    'bryan@novaguardian.online': 'WEDw6978',
    'daniela@novaguardian.online': 'ymez6926'
}

print("-- Actualizar contraseñas con bcrypt")
for email, pwd in passwords.items():
    h = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(rounds=12))
    print(f"UPDATE users SET password_hash = '{h.decode('utf-8')}' WHERE email = '{email}';")
