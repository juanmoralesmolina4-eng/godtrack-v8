from typing import List, Dict, Optional
from models import LapInput, EngineeringSetup, SessionStatus

class RaceState:
    """
    Centralized State Management for Godtrack Session.
    Replaces the global dictionary with a structured singleton-like pattern.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.laps: List[LapInput] = []
        self.current_fuel: float = 120.0
        self.current_wear: float = 0.0
        self.best_lap: float = float('inf')
        self.best_s1: float = float('inf')
        self.best_s2: float = float('inf')
        self.best_s3: float = float('inf')
        self.current_setup: EngineeringSetup = EngineeringSetup()
        
    def add_lap(self, lap: LapInput):
        self.laps.append(lap)
        self.current_fuel = lap.fuel_remaining
        self.current_wear = lap.tyre_wear
        
        # Update Bests
        if lap.lap_time < self.best_lap: self.best_lap = lap.lap_time
        if lap.s1 and lap.s1 < self.best_s1: self.best_s1 = lap.s1
        if lap.s2 and lap.s2 < self.best_s2: self.best_s2 = lap.s2
        if lap.s3 and lap.s3 < self.best_s3: self.best_s3 = lap.s3
        
    def get_best_sectors(self) -> Dict[str, float]:
        return {
            "s1": self.best_s1,
            "s2": self.best_s2,
            "s3": self.best_s3
        }

    def get_theoretical_lap(self) -> float:
        theo = self.best_s1 + self.best_s2 + self.best_s3
        return 0.0 if theo == float('inf') else theo
        
    def get_session_status(self, last_lap: Optional[LapInput] = None, msg: str = "OK") -> SessionStatus:
        """Helper to generate the API response object"""
        if not last_lap and self.laps:
            last_lap = self.laps[-1]
        
        # Fallback values if no laps
        l_time = last_lap.lap_time if last_lap else 0.0
        s1 = last_lap.s1 if last_lap else 0.0
        s2 = last_lap.s2 if last_lap else 0.0
        s3 = last_lap.s3 if last_lap else 0.0
        fuel = last_lap.fuel_remaining if last_lap else self.current_fuel
        wear = last_lap.tyre_wear if last_lap else self.current_wear
        
        # --- CALCULATIONS ---
        
        # 1. Delta
        delta = 0.0
        if last_lap and self.best_lap != float('inf'):
            delta = l_time - self.best_lap
            
        # 2. Fuel Estimation
        est_laps = 0.0
        if fuel > 0 and len(self.laps) > 1:
            # Calculate avg consumption from history
            # Simple heuristic: Take last 5 laps or all laps
            recent = self.laps[-5:] if len(self.laps) > 5 else self.laps
            consumptions = []
            for i in range(len(recent)-1):
                diff = recent[i].fuel_remaining - recent[i+1].fuel_remaining
                if diff > 0: consumptions.append(diff)
            
            avg_cons = (sum(consumptions) / len(consumptions)) if consumptions else 0.0
            if avg_cons > 0:
                est_laps = fuel / avg_cons
        elif fuel > 0:
             # Fallback for first lap (assume standard ~2.5kg consumption)
             est_laps = fuel / 2.5

        return SessionStatus(
            current_lap=len(self.laps),
            last_lap_time=l_time,
            s1=s1, s2=s2, s3=s3,
            fuel=fuel,
            tyre_wear=wear,
            engineer_message=msg,
            best_lap=self.best_lap if self.best_lap != float('inf') else 0.0,
            best_s1=self.best_s1 if self.best_s1 != float('inf') else 0.0,
            best_s2=self.best_s2 if self.best_s2 != float('inf') else 0.0,
            best_s3=self.best_s3 if self.best_s3 != float('inf') else 0.0,
            theoretical_lap=self.get_theoretical_lap(),
            current_setup=self.current_setup,
            delta_to_best=round(delta, 3),
            est_laps_remaining=round(est_laps, 1)
        )

# Global Instance
state = RaceState()
