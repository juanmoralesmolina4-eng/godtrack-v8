import requests
import time

BASE_URL = "http://localhost:8000/api"

def test_new_features():
    print("Testing New Engineering Features...")

    # 1. Test Setup Endpoint
    setup = {
        "front_wing": 8,
        "rear_wing": 2,
        "suspension_stiffness": 7,
        "brake_bias": 54,
        "diff_lock": 60,
        "pressure_front": 23.5,
        "pressure_rear": 23.5
    }
    res = requests.post(f"{BASE_URL}/setup", json=setup)
    assert res.status_code == 200
    data = res.json()
    assert data["front_wing"] == 8
    print("[PASS] Save Setup")
    
    res = requests.get(f"{BASE_URL}/setup")
    assert res.json()["rear_wing"] == 2
    print("[PASS] Load Setup")

    # 2. Test Telemetry Upload
    csv_content = """Time,S1,S2,S3,Fuel
105.0,30.0,40.0,35.0,10.0
104.5,29.8,39.9,34.8,9.0
"""
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    res = requests.post(f"{BASE_URL}/upload_telemetry", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["laps_added"] == 2
    print("[PASS] CSV Upload")

    print("\nENGINEERING TESTS PASSED")

if __name__ == "__main__":
    test_new_features()
