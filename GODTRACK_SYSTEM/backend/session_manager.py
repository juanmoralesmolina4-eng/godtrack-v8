import os
import json
import shutil
from typing import List, Dict, Any
from models import LapInput

DATA_DIR = "data/sessions"

class SessionManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            
    def save_session(self, data: Dict[str, Any]) -> str:
        """
        Saves ingested data as a new session.
        Returns the filename/ID.
        """
        # Auto-name: Race_1, Race_2, etc.
        existing = len(os.listdir(DATA_DIR))
        name = f"Carrera_{existing + 1}"
        if "name" in data and data["name"]:
            name = f"Carrera_{existing + 1}_{data['name']}"
            
        # Convert objects to dicts for JSON
        laps_out = []
        for lap in data["laps"]:
            if hasattr(lap, "dict"): laps_out.append(lap.dict())
            else: laps_out.append(lap) # Already dict?
            
        final_obj = {
            "id": name,
            "meta": data["stats"],
            "laps": laps_out,
            "created_at": "Today" # simplified
        }
        
        path = os.path.join(DATA_DIR, f"{name}.json")
        with open(path, 'w') as f:
            json.dump(final_obj, f, indent=2)
            
        return name

    def list_sessions(self) -> List[Dict]:
        """Returns list of available sessions with metadata"""
        sessions = []
        for f in os.listdir(DATA_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(DATA_DIR, f), 'r') as buf:
                        d = json.load(buf)
                        sessions.append({
                            "id": d["id"],
                            "laps": len(d["laps"]),
                            "best": d["meta"].get("best_lap", 0),
                            "fuel_burn": d["meta"].get("est_fuel_burn", 0)
                        })
                except: continue
        return sorted(sessions, key=lambda x: x["id"], reverse=True)

    def load_session(self, session_id: str) -> Dict:
        path = os.path.join(DATA_DIR, f"{session_id}.json")
        if not os.path.exists(path): return None
        with open(path, 'r') as f:
            return json.load(f)

    def delete_session(self, session_id: str):
         path = os.path.join(DATA_DIR, f"{session_id}.json")
         if os.path.exists(path): os.remove(path)
