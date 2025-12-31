import re
import pandas as pd
import io
from typing import List, Dict, Any
from models import LapInput

class SmartIngestor:
    """
    GODTRACK V8 UNIVERSAL INGESTOR
    "It reads what you feed it."
    """
    
    def ingest(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Main entry point. 
        """
        laps = []
        stats = {}
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', filename.split('.')[0])
        
        # 1. Determine Type
        is_excel = filename.lower().endswith('.xlsx') or filename.lower().endswith('.xls')
        
        if is_excel:
            try:
                df = pd.read_excel(io.BytesIO(file_content))
                # Convert to string lines for regex processing or process DF directly
                # For consistency with the heuristic engine, we'll convert interesting cols to text
                text_blob = df.to_string()
                lines = text_blob.splitlines()
            except Exception as e:
                raise ValueError(f"Excel Parse Error: {e}")
        else:
            # Text / CSV
            text = self._decode(file_content)
            lines = text.splitlines()

        # 2. Semantic Check (God Mode Intelligence)
        # Check if this is a Street Map (User's specific case)
        street_markers = ["codi_via", "carrer de", "avinguda", "plaça de", "tipus_via"]
        is_map = False
        sample = "\n".join(lines[:20]).lower()
        if any(m in sample for m in street_markers):
            is_map = True
            
        if is_map:
            # Special Handling: It's a map.
            # We can't extract laps, but we can return a "Session" that acknowledges it.
            return {
                "name": clean_name + "_MAP",
                "laps": [],
                "stats": {
                    "note": "STREET DATABASE DETECTED",
                    "streets_found": len(lines),
                    "best_lap": 0,
                    "avg_pace": 0,
                    "est_fuel_burn": 0
                }
            }

        # 3. Extract Laps using Pattern Matching
        laps = self._extract_laps(lines)
        
        if not laps:
            # Fallback: Did we fail to find times?
            raise ValueError("No lap data detected. Format unrecognized.")
            
        # 4. Calculate Stats
        stats = self._calc_stats(laps)
        
        return {
            "name": clean_name,
            "laps": laps,
            "stats": stats
        }

    def _decode(self, content: bytes) -> str:
        encodings = ['utf-8', 'latin-1', 'utf-16', 'cp1252']
        for enc in encodings:
            try:
                return content.decode(enc)
            except: continue
        return content.decode('utf-8', errors='replace')

    def _extract_laps(self, lines: List[str]) -> List[LapInput]:
        laps = []
        
        # Regex patterns
        # Time: looks for 1:23.456, 83.456, 1.23.456
        time_pattern = re.compile(r'(?:(\d{1,2})[:.])?(\d{1,2})[.,](\d{1,4})') 
        
        for line in lines:
            if len(line) < 5: continue
            
            # Find all time-like strings
            times = time_pattern.findall(line)
            if not times: continue
            
            valid_seconds = []
            for match in times:
                m, s, ms = match
                
                # Normalize
                seconds = 0.0
                if m: seconds += float(m) * 60
                seconds += float(s)
                # handle ms logic (if length is 3, divide by 1000, etc? standard is just float)
                # just append 0.ms
                seconds += float(f"0.{ms}")
                
                # Filter noise: Laps usually aren't 1s or 5000s
                if 20.0 < seconds < 300.0:
                    valid_seconds.append(seconds)
            
            if not valid_seconds: continue
            
            # Sort? Usually the largest is the full lap, smaller are sectors?
            # Or first is Lap?
            # heuristic: Max value is likely the lap time.
            lap_time = max(valid_seconds)
            
            # Fuel? Look for numbers followed by kg, l, lit, %
            fuel_val = 0.0
            fuel_search = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|l|lit|%)', line.lower())
            if fuel_search:
                fuel_val = float(fuel_search.group(1))
            
            # Auto-calc sectors
            s1 = lap_time * 0.3
            s2 = lap_time * 0.4
            s3 = lap_time * 0.3
            
            laps.append(LapInput(
                lap_time=lap_time,
                s1=s1, s2=s2, s3=s3,
                fuel_remaining=fuel_val,
                tyre_wear=0.0,
                is_pit_stop=False
            ))
            
        return laps

    def _calc_stats(self, laps: List[LapInput]) -> Dict:
        if not laps: return {}
        times = [l.lap_time for l in laps]
        fuels = [l.fuel_remaining for l in laps if l.fuel_remaining > 0]
        
        avg_pace = sum(times) / len(times)
        best_lap = min(times)
        
        fuel_burn = 0.0
        if len(fuels) > 1:
            # Simple diff average
            burns = []
            for i in range(len(fuels)-1):
                diff = fuels[i] - fuels[i+1]
                if diff > 0: burns.append(diff)
            if burns:
                fuel_burn = sum(burns) / len(burns)
                
        return {
            "total_laps": len(laps),
            "best_lap": best_lap,
            "avg_pace": avg_pace,
            "est_fuel_burn": fuel_burn
        }
