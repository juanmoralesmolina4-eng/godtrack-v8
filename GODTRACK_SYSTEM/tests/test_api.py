import requests
import time

BASE_URL = "http://localhost:8000/api"

def test_backend():
    print("Testing Backend...")
    
    # 1. Reset Session
    try:
        res = requests.get(f"{BASE_URL}/reset")
        assert res.status_code == 200
        print("[PASS] Reset Session")
    except Exception as e:
        print(f"[FAIL] Backend might not be running: {e}")
        return

    # 2. Add Lap (Dry)
    lap_data = {
        "lap_time": 105.5,
        "s1": 30.0,
        "s2": 40.0,
        "s3": 35.5,
        "fuel_remaining": 98.0,
        "tyre_wear": 0.05,
        "is_pit_stop": False,
        "weather_cond": "dry",
        "air_temp": 22.0
    }
    res = requests.post(f"{BASE_URL}/lap", json=lap_data)
    assert res.status_code == 200
    data = res.json()
    assert data["current_lap"] == 1
    assert data["best_lap"] == 105.5
    print("[PASS] Submit Lap (Dry)")

    # 3. Add Lap (Wet - Faster to check best update logic)
    lap_data["lap_time"] = 104.0
    lap_data["fuel_remaining"] = 95.0
    res = requests.post(f"{BASE_URL}/lap", json=lap_data)
    data = res.json()
    assert data["best_lap"] == 104.0
    print("[PASS] Submit Lap (Improvement)")

    # 4. Simulation
    sim_input = {
        "car_class": "GT3",
        "initial_fuel": 50,
        "laps_to_simulate": 5,
        "tyre_compound": "med"
    }
    res = requests.post(f"{BASE_URL}/simulate", json=sim_input)
    assert res.status_code == 200
    results = res.json()
    assert len(results) == 5
    print("[PASS] Stint Simulation")

    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    test_backend()
