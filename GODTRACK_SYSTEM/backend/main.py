from fastapi import FastAPI, UploadFile, File
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from models import LapInput, SimulationInput, SimulationResult, SessionStatus, EngineeringSetup, Profile
from physics import PhysicsEngine

# OPTIMIZATION: State & Ingestor
from state_manager import state
from ingestor import SmartIngestor
from session_manager import SessionManager

import socket
import logging
import webbrowser
import os
import threading
import sys
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    pass

app = FastAPI(title="GODTRACK Strategy System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

frontend_path = get_resource_path("frontend")
if not os.path.exists(frontend_path):
    potential_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    if os.path.exists(potential_path):
        frontend_path = potential_path

engine = PhysicsEngine()
profiles_db: Dict[str, Profile] = {}
v8_ingestor = SmartIngestor()
v8_sessions = SessionManager()

# --- ROUTES ---

@app.get("/api/reset")
def reset_session():
    state.reset()
    return {"message": "Session Reset. Race Start."}

@app.post("/api/setup", response_model=EngineeringSetup)
def update_setup(setup: EngineeringSetup):
    state.current_setup = setup
    return setup

@app.get("/api/setup", response_model=EngineeringSetup)
def get_setup():
    return state.current_setup

# --- PROFILE ENDPOINTS ---
@app.get("/api/profiles", response_model=List[str])
def list_profiles():
    return list(profiles_db.keys())

@app.post("/api/profiles/save")
def save_profile(profile: Profile):
    profiles_db[profile.name] = profile
    return {"status": "success", "message": f"Profile '{profile.name}' saved."}

@app.get("/api/profiles/load/{name}", response_model=Profile)
def load_profile(name: str):
    if name in profiles_db:
        p = profiles_db[name]
        state.current_setup = p.setup
        return p
    return {"error": "Profile not found"}

# --- TELEMETRY ---
@app.get("/api/laps", response_model=List[SessionStatus])
def get_laps():
    """Returns the full history of the current session"""
    history = []
    # Reconstruct history using state helper
    # Optimization: We could store history in state, but this is fine for now
    running_state = state.laps # This is the list
    # Actually we need to return SessionStatus snapshots. 
    # For now, let's just return the last status repeatedly? No, user wants history.
    # Simple reconstruction:
    temp_best_lap = float('inf')
    
    for i, lap in enumerate(state.laps):
        if lap.lap_time < temp_best_lap: temp_best_lap = lap.lap_time
        
        history.append(SessionStatus(
            current_lap=i+1,
            last_lap_time=lap.lap_time,
            s1=lap.s1, s2=lap.s2, s3=lap.s3,
            fuel=lap.fuel_remaining,
            tyre_wear=lap.tyre_wear,
            engineer_message="HISTORY",
            best_lap=temp_best_lap,
            best_s1=0, best_s2=0, best_s3=0, # simplified history
            theoretical_lap=0,
            current_setup=state.current_setup
        ))
    return history

@app.post("/api/upload_telemetry")
async def upload_telemetry(file: UploadFile = File(...)):
    """LEGACY ROUTE REDIRECTED TO V8 ENGINE"""
    content = await file.read()
    try:
        # V8 Ingest
        data = v8_ingestor.ingest(content, file.filename)
        
        # Load into state immediately (Legacy behavior expected immediate load)
        state.reset()
        for lap in data["laps"]:
            state.add_lap(lap)
            
        return {"status": "success", "message": f"Imported {len(data['laps'])} laps via V8", "laps_processed": len(data['laps'])}
    except Exception as e:
        return {"status": "error", "message": f"Parse Error: {str(e)}"}

@app.post("/api/lap", response_model=SessionStatus)
def submit_lap(lap_data: LapInput):
    # Analyze
    msg = engine.analyze_telemetry(lap_data, state.get_best_sectors())
    
    # Update State
    state.add_lap(lap_data)
    
    return state.get_session_status(last_lap=lap_data, msg=msg)

@app.post("/api/simulate", response_model=List[SimulationResult])
def simulate_stint(sim_data: SimulationInput):
    results = []
    current_fuel = sim_data.initial_fuel
    current_wear = 0.0 
    
    sim_setup = state.current_setup
    profile = engine.profiles.get(sim_data.car_class, engine.profiles["GT3"])
    
    for lap in range(1, sim_data.laps_to_simulate + 1):
        est_time = engine.calculate_pace(
            sim_data.car_class, 
            current_fuel, 
            current_wear,
            "dry", # simplified
            22.0,
            sim_setup
        )
        
        status_msg = "OK"
        if current_fuel <= 0: status_msg = "DNF (NO FUEL)"
        if current_wear >= 1.0: status_msg = "DNF (TYRE FAILURE)"

        results.append(SimulationResult(
            lap=lap,
            estimated_time=est_time,
            fuel_remaining=round(current_fuel, 2),
            tyre_wear=round(current_wear, 2),
            message=status_msg
        ))
        
        current_fuel -= profile["fuel_consumption"]
        current_wear += profile["deg_rate"]

        if sim_data.pit_stop_lap and lap == sim_data.pit_stop_lap:
            current_fuel = profile["tank_capacity"]
            current_wear = 0.0
            results[-1].estimated_time += 25.0 
            results[-1].message = "BOX BOX"

    return results

# --- V8 SPECIFIC ---
@app.post("/api/v8/ingest")
async def ingest_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        data = v8_ingestor.ingest(content, file.filename)
        session_id = v8_sessions.save_session(data)
        return {"status": "success", "session_id": session_id, "stats": data["stats"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/v8/sessions")
def list_sessions_v8():
    return v8_sessions.list_sessions()

@app.get("/api/v8/load/{session_id}")
def load_session_v8(session_id: str):
    data = v8_sessions.load_session(session_id)
    if not data: return {"status": "error", "message": "Not found"}
    
    state.reset()
    # If it's a map session, we might not have laps to add, handled gracefully
    for l in data["laps"]:
        state.add_lap(LapInput(**l))
        
    return {"status": "success", "message": f"Loaded {len(data['laps'])} laps"}

@app.delete("/api/v8/delete/{session_id}")
def delete_session_v8(session_id: str):
    v8_sessions.delete_session(session_id)
    return {"status": "success"}

@app.get("/api/weather")
def get_weather():
    env = state.current_setup.environment
    return {
        "air_temp": env.air_temp,
        "track_temp": env.track_temp,
        "wind_speed": env.wind_speed,
        "wind_direction": env.wind_direction,
        "rain_intensity": env.rain_intensity,
        "track_wetness": (env.rain_intensity / 100.0)
    }

# MOUNT STATIC LAST
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

if __name__ == '__main__':
    import uvicorn
    import time
    def find_free_port(start_port=8000):
        port = start_port
        while port < 65535:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(('localhost', port)) != 0:
                    return port
                port += 1
        return start_port

    try:
        port = find_free_port()
        host = '0.0.0.0'
        url = f"http://localhost:{port}"

        print("\n" + "="*50)
        print(f"GODTRACK SYSTEM OPTIMIZED V8")
        print(f"Access the application at: {url}")
        print("="*50 + "\n")

        def launch_browser():
            print(f"Attempting to open browser at {url}...")
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"Manual open required: {url}")

        threading.Timer(2.0, launch_browser).start()
        uvicorn.run(app, host=host, port=port, log_level="info")

    except Exception as e:
        print(f"CRITICAL: {e}")
        input("Press Enter...")

from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from models import LapInput, SimulationInput, SimulationResult, SessionStatus, EngineeringSetup, Profile
from physics import PhysicsEngine
from csv_parser import parse_telemetry_csv

import socket
import logging





@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    # We will handle browser opening in the main block or here
    yield
    # Shutdown logic
    pass

app = FastAPI(title="GODTRACK Strategy System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import webbrowser
import os
import threading
import sys

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Mount frontend directory
frontend_path = get_resource_path("frontend")
# Fallback logic for dev environment vs frozen exe
if not os.path.exists(frontend_path):
    potential_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    if os.path.exists(potential_path):
        frontend_path = potential_path




engine = PhysicsEngine()

# In-memory database for profiles
profiles_db: Dict[str, Profile] = {}

# Session State
session_state = {
    "laps": [],
    "current_fuel": 120.0,
    "current_wear": 0.0,
    "best_lap": float('inf'),
    "best_s1": float('inf'),
    "best_s2": float('inf'),
    "best_s3": float('inf'),
    "current_setup": EngineeringSetup()
}

@app.get("/api/reset")
def reset_session():
    session_state["laps"] = []
    session_state["current_fuel"] = 120.0
    session_state["current_wear"] = 0.0
    session_state["best_lap"] = float('inf')
    session_state["best_s1"] = float('inf')
    session_state["best_s2"] = float('inf')
    session_state["best_s3"] = float('inf')
    return {"message": "Session Reset. Race Start."}

# --- SETUP ENDPOINTS ---
@app.post("/api/setup", response_model=EngineeringSetup)
def update_setup(setup: EngineeringSetup):
    session_state["current_setup"] = setup
    return setup

@app.get("/api/setup", response_model=EngineeringSetup)
def get_setup():
    return session_state["current_setup"]

# --- PROFILE ENDPOINTS ---
@app.get("/api/profiles", response_model=List[str])
def list_profiles():
    return list(profiles_db.keys())

@app.post("/api/profiles/save")
def save_profile(profile: Profile):
    profiles_db[profile.name] = profile
    return {"status": "success", "message": f"Profile '{profile.name}' saved."}

@app.get("/api/profiles/load/{name}", response_model=Profile)
def load_profile(name: str):
    if name in profiles_db:
        p = profiles_db[name]
        session_state["current_setup"] = p.setup
        return p
    return {"error": "Profile not found"}

# --- TELEMETRY ---
@app.get("/api/laps", response_model=List[SessionStatus])
def get_laps():
    """Returns the full history of the current session"""
    history = []
    # Reconstruct SessionStatus for each lap (simplified)
    # Ideally we'd store the full status, but rebuilding is fine for now
    for i, lap in enumerate(session_state["laps"]):
        # Calculate theo for that point in time? No, just current bests
        history.append(SessionStatus(
            current_lap=i+1,
            last_lap_time=lap.lap_time,
            s1=lap.s1, s2=lap.s2, s3=lap.s3,
            fuel=lap.fuel_remaining,
            tyre_wear=lap.tyre_wear,
            engineer_message="HISTORY",
            best_lap=session_state["best_lap"],
            best_s1=session_state["best_s1"], best_s2=session_state["best_s2"], best_s3=session_state["best_s3"],
            theoretical_lap=0.0,
            current_setup=session_state["current_setup"]
        ))
    return history

@app.post("/api/upload_telemetry")
async def upload_telemetry(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        laps = parse_telemetry_csv(contents)
        if not laps:
            return {"status": "error", "message": "No valid laps found or CSV format unknown."}
        
        count = 0
        for lap in laps:
            submit_lap(lap)
            count += 1
            
        return {"status": "success", "message": f"Imported {count} laps", "laps_processed": count}
    except Exception as e:
        return {"status": "error", "message": f"Parse Error: {str(e)}"}

@app.post("/api/lap", response_model=SessionStatus)
def submit_lap(lap_data: LapInput):
    session_state["current_fuel"] = lap_data.fuel_remaining
    session_state["current_wear"] = lap_data.tyre_wear
    
    # Track Bests
    if lap_data.lap_time < session_state["best_lap"]:
        session_state["best_lap"] = lap_data.lap_time
    if lap_data.s1 and lap_data.s1 < session_state["best_s1"]: session_state["best_s1"] = lap_data.s1
    if lap_data.s2 and lap_data.s2 < session_state["best_s2"]: session_state["best_s2"] = lap_data.s2
    if lap_data.s3 and lap_data.s3 < session_state["best_s3"]: session_state["best_s3"] = lap_data.s3

    best_sectors = {
        "s1": session_state["best_s1"],
        "s2": session_state["best_s2"],
        "s3": session_state["best_s3"]
    }

    msg = engine.analyze_telemetry(lap_data, best_sectors)
    
    session_state["laps"].append(lap_data)

    theo_lap = session_state["best_s1"] + session_state["best_s2"] + session_state["best_s3"]
    if theo_lap == float('inf'): theo_lap = 0.0

    return SessionStatus(
        current_lap=len(session_state["laps"]),
        last_lap_time=lap_data.lap_time,
        s1=lap_data.s1 or 0.0,
        s2=lap_data.s2 or 0.0,
        s3=lap_data.s3 or 0.0,
        fuel=lap_data.fuel_remaining,
        tyre_wear=lap_data.tyre_wear,
        engineer_message=msg,
        best_lap=session_state["best_lap"] if session_state["best_lap"] != float('inf') else 0.0,
        best_s1=session_state["best_s1"] if session_state["best_s1"] != float('inf') else 0.0,
        best_s2=session_state["best_s2"] if session_state["best_s2"] != float('inf') else 0.0,
        best_s3=session_state["best_s3"] if session_state["best_s3"] != float('inf') else 0.0,
        theoretical_lap=theo_lap,
        current_setup=session_state["current_setup"]
    )

@app.post("/api/simulate", response_model=List[SimulationResult])
def simulate_stint(sim_data: SimulationInput):
    results = []
    current_fuel = sim_data.initial_fuel
    current_wear = 0.0 
    
    sim_setup = session_state["current_setup"]
    profile = engine.profiles.get(sim_data.car_class, engine.profiles["GT3"])
    
    for lap in range(1, sim_data.laps_to_simulate + 1):
        est_time = engine.calculate_pace(
            sim_data.car_class, 
            current_fuel, 
            current_wear,
            "dry",
            22.0,
            sim_setup
        )
        
        status_msg = "OK"
        if current_fuel <= 0: status_msg = "DNF (NO FUEL)"
        if current_wear >= 1.0: status_msg = "DNF (TYRE FAILURE)"

        results.append(SimulationResult(
            lap=lap,
            estimated_time=est_time,
            fuel_remaining=round(current_fuel, 2),
            tyre_wear=round(current_wear, 2),
            message=status_msg
        ))
        
        current_fuel -= profile["fuel_consumption"]
        current_wear += profile["deg_rate"]

        if sim_data.pit_stop_lap and lap == sim_data.pit_stop_lap:
            current_fuel = profile["tank_capacity"]
            current_wear = 0.0
            results[-1].estimated_time += 25.0 
            results[-1].message = "BOX BOX"

    return results

# --- GODTRACK V8: UNIVERSAL DATA & SESSIONS ---
from ingestor import SmartIngestor
from session_manager import SessionManager

v8_ingestor = SmartIngestor()
v8_sessions = SessionManager()

@app.post("/api/v8/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """Universal File Reader -> New Session"""
    content = await file.read()
    try:
        # 1. Ingest
        data = v8_ingestor.ingest(content, file.filename)
        # 2. Save
        session_id = v8_sessions.save_session(data)
        return {"status": "success", "session_id": session_id, "stats": data["stats"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/v8/sessions")
def list_sessions_v8():
    return v8_sessions.list_sessions()

@app.get("/api/v8/load/{session_id}")
def load_session_v8(session_id: str):
    data = v8_sessions.load_session(session_id)
    if not data: return {"status": "error", "message": "Not found"}
    
    # LOAD INTO STATE
    session_state["laps"] = []
    # convert dicts back to objects if needed, or just append dicts (Pydantic models usually preferred)
    # The app uses LapInput objects.
    
    # Clear current
    session_state["laps"] = []
    
    loaded_laps = []
    for l in data["laps"]:
        obj = LapInput(**l)
        loaded_laps.append(obj)
        
    session_state["laps"] = loaded_laps
    
    # Recalculate Bests
    reset_session() # clear bests
    session_state["laps"] = loaded_laps # restore laps
    for obj in loaded_laps:
         if obj.lap_time < session_state["best_lap"]: session_state["best_lap"] = obj.lap_time
         if obj.s1 < session_state["best_s1"]: session_state["best_s1"] = obj.s1
         if obj.s2 < session_state["best_s2"]: session_state["best_s2"] = obj.s2
         if obj.s3 < session_state["best_s3"]: session_state["best_s3"] = obj.s3
         
         # Last fuel state
         session_state["current_fuel"] = obj.fuel_remaining
         
    return {"status": "success", "message": f"Loaded {len(loaded_laps)} laps from {session_id}"}
    
@app.delete("/api/v8/delete/{session_id}")
def delete_session_v8(session_id: str):
    v8_sessions.delete_session(session_id)
    return {"status": "success"}

@app.get("/api/weather")
def get_weather():
    env = session_state["current_setup"].environment
    # specific logic for track_wetness could be complex, but for now simple mapping
    return {
        "air_temp": env.air_temp,
        "track_temp": env.track_temp,
        "wind_speed": env.wind_speed,
        "wind_direction": env.wind_direction,
        "rain_intensity": env.rain_intensity,
        "track_wetness": (env.rain_intensity / 100.0)
    }

app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

if __name__ == '__main__':
    import uvicorn
    import time

    def find_free_port(start_port=8000):
        port = start_port
        while port < 65535:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(('localhost', port)) != 0:
                    return port
                port += 1
        return start_port

    try:
        port = find_free_port()
        host = '0.0.0.0'
        url = f"http://localhost:{port}"

        print("\n" + "="*50)
        print(f"GODTRACK SYSTEM INITIATING...")
        print(f"Access the application at: {url}")
        print("="*50 + "\n")

        def launch_browser():
            print(f"Attempting to open browser at {url}...")
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"Could not automatically open browser: {e}")
                print(f"Please manually open: {url}")

        # Launch browser after a short delay to allow server startup
        threading.Timer(2.0, launch_browser).start()
        
        uvicorn.run(app, host=host, port=port, log_level="info")

    except Exception as e:
        print("\n" + "!"*50)
        print(f"CRITICAL ERROR: {e}")
        print("!"*50 + "\n")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nApplication has stopped.")
        input("Press Enter to exit...")

