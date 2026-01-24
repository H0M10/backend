import requests
import json

BASE_URL = "http://localhost:8002/api/v1"

# Test Login
print("=" * 60)
print("TESTING LOGIN")
print("=" * 60)

response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": "hanniel@novaguardian.online",
        "password": "Test123456"
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("✅ LOGIN EXITOSO!")
    print(f"Access Token: {data['access_token'][:50]}...")
    print(f"User: {data['user']['name']}")
    print(f"Email: {data['user']['email']}")
    
    # Test protected endpoint
    print("\n" + "=" * 60)
    print("TESTING PROTECTED ENDPOINT /auth/me")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"Status: {me_response.status_code}")
    if me_response.status_code == 200:
        print("✅ ENDPOINT PROTEGIDO OK!")
        print(json.dumps(me_response.json(), indent=2))
    else:
        print("❌ Error:", me_response.text)
    
    # Test monitored persons
    print("\n" + "=" * 60)
    print("TESTING /monitored-persons")
    print("=" * 60)
    
    mp_response = requests.get(f"{BASE_URL}/monitored-persons", headers=headers)
    print(f"Status: {mp_response.status_code}")
    if mp_response.status_code == 200:
        persons = mp_response.json()
        print(f"✅ Personas monitoreadas: {len(persons)}")
        for p in persons:
            print(f"  - {p['name']} ({p.get('relationship', 'N/A')})")
    else:
        print("❌ Error:", mp_response.text)
    
    # Test devices
    print("\n" + "=" * 60)
    print("TESTING /devices")
    print("=" * 60)
    
    dev_response = requests.get(f"{BASE_URL}/devices", headers=headers)
    print(f"Status: {dev_response.status_code}")
    if dev_response.status_code == 200:
        devices = dev_response.json()
        print(f"✅ Dispositivos: {len(devices)}")
        for d in devices:
            print(f"  - {d['code']} | Bateria: {d['batteryLevel']}% | Status: {d['status']}")
    else:
        print("❌ Error:", dev_response.text)
    
    # Test alerts
    print("\n" + "=" * 60)
    print("TESTING /alerts")
    print("=" * 60)
    
    alerts_response = requests.get(f"{BASE_URL}/alerts", headers=headers)
    print(f"Status: {alerts_response.status_code}")
    if alerts_response.status_code == 200:
        alerts = alerts_response.json()
        print(f"✅ Alertas: {len(alerts)}")
        for a in alerts[:3]:
            print(f"  - [{a['severity'].upper()}] {a['title']}")
    else:
        print("❌ Error:", alerts_response.text)
    
    # Test dashboard
    print("\n" + "=" * 60)
    print("TESTING /dashboard/summary")
    print("=" * 60)
    
    dash_response = requests.get(f"{BASE_URL}/dashboard/summary", headers=headers)
    print(f"Status: {dash_response.status_code}")
    if dash_response.status_code == 200:
        print("✅ Dashboard OK!")
        print(json.dumps(dash_response.json(), indent=2))
    else:
        print("❌ Error:", dash_response.text)

else:
    print("❌ LOGIN FALLIDO!")
    print(response.text)

print("\n" + "=" * 60)
print("TESTS COMPLETADOS")
print("=" * 60)
