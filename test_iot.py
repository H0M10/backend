import requests
import json

BASE = 'http://localhost:8002/api/v1'

# Login
print("=== Probando Login ===")
r = requests.post(f'{BASE}/auth/login', json={
    'email': 'hanniel@novaguardian.online',
    'password': 'Test123456'
})
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2))

if data.get('success'):
    token = data['data']['token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Obtener dispositivos
    print("\n=== Dispositivos ===")
    r = requests.get(f'{BASE}/devices', headers=headers)
    devices = r.json()
    print(json.dumps(devices, indent=2, default=str)[:500])
    
    if devices.get('success') and devices['data']:
        device_id = devices['data'][0]['id']
        
        # Probar endpoint de monitoreo con IoT Simulator
        print(f"\n=== Vitales del dispositivo {device_id} ===")
        r = requests.get(f'{BASE}/monitoring/{device_id}/current', headers=headers)
        print(json.dumps(r.json(), indent=2, default=str))
        
        print(f"\n=== Ubicación del dispositivo ===")
        r = requests.get(f'{BASE}/monitoring/{device_id}/location', headers=headers)
        print(json.dumps(r.json(), indent=2, default=str))
else:
    print("Login fallido")
