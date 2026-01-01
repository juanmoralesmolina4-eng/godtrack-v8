import math
from models import EngineeringSetup, TrackEnvironment

class PhysicsEngine:
    def __init__(self):
        # Base Vehicle Profiles (Performance Baselines)
        # Optimized for a balanced circuit (e.g. Barcelona)
        self.profiles = {
            "GT3": {
                "mass": 1250, 
                "tank_capacity": 120,
                "base_lap_time": 105.0, # 1:45.0
                "fuel_consumption": 2.8,
                "deg_rate": 0.04,
                "fuel_penalty": 0.04, # Time lost per kg of fuel
                "drag_coeff": 0.35,
                "downforce_coeff": 1.2
            },
            "F1": {
                "mass": 798,
                "tank_capacity": 110,
                "base_lap_time": 80.0, # 1:20.0
                "fuel_consumption": 1.8,
                "deg_rate": 0.10,
                "fuel_penalty": 0.03,
                "drag_coeff": 0.7, # High drag due to open wheels/wings
                "downforce_coeff": 3.5
            },
            "LMP": {
                "mass": 930,
                "tank_capacity": 90,
                "base_lap_time": 95.0,
                "fuel_consumption": 2.0,
                "deg_rate": 0.06,
                "fuel_penalty": 0.035,
                "drag_coeff": 0.4,
                "downforce_coeff": 2.5
            },
             "Kart": {
                "mass": 150,
                "tank_capacity": 10,
                "base_lap_time": 50.0, 
                "fuel_consumption": 0.5,
                "deg_rate": 0.015,
                "fuel_penalty": 0.01,
                "drag_coeff": 0.6, # Human brick
                "downforce_coeff": 0.1
            }
        }
    
    def calculate_pace(self, car_class: str, fuel: float, wear: float, weather_cond="dry", temp=25.0, setup: EngineeringSetup = None) -> float:
        """
        MASTER CALCULATION ENGINE
        Combines Mass, Aero, Suspension, Engine, Environment, and Tyre physics.
        """
        p = self.profiles.get(car_class, self.profiles["GT3"])
        
        # --- 1. BASELINE ---
        current_time = p["base_lap_time"]
        
        # --- 2. MASS PENALTY (Fuel) ---
        # Fuel adds weight -> worse accel, braking, and cornering
        fuel_delta = (p["tank_capacity"] - fuel) * p["fuel_penalty"]
        current_time -= fuel_delta # Less fuel = Faster

        # --- 3. TYRE DEGRADATION (Complex Curve) ---
        # Non-linear falloff. Fine until 40%, then drops, then cliff at 70%
        deg_factor = 0.0
        if wear < 0.3: deg_factor = wear * 0.5 
        elif wear < 0.6: deg_factor = 0.15 + (wear - 0.3) * 2.0
        else: deg_factor = 0.75 + (wear - 0.6) * 6.0
        
        # Compound Impact
        compound_offset = 0.0
        if setup and setup.tyres:
            c = setup.tyres.compound
            if c == "slick_soft": 
                compound_offset = -1.2 # Faster base
                deg_factor *= 1.5 # Higher deg
            elif c == "slick_hard":
                compound_offset = +0.8 # Slower base
                deg_factor *= 0.6 # Lower deg
        
        current_time += deg_factor
        current_time += compound_offset

        # --- 4. SETUP PHYSICS (The "God Mode" logic) ---
        if setup:
            current_time += self._calculate_setup_impact(setup, p)

        # --- 5. ENVIRONMENT ---
        env_impact = 0.0
        if setup and setup.environment:
            env = setup.environment
            # Track Temp: Optimal is ~30C. 
            temp_dev = abs(env.track_temp - 30.0)
            env_impact += temp_dev * 0.02
            
            # Wind: Headwind (N) vs Tailwind (S)
            if env.wind_direction == "N": env_impact -= (env.wind_speed / 100.0) 
            elif env.wind_direction == "S": env_impact += (env.wind_speed / 100.0)

            # --- RAIN LOGIC ---
            # Rain is the great equalizer.
            # 0-10% = Greasy (+1s)
            # 10-50% = Wet (+5s to +10s)
            # >50% = Monsoon (+20s)
            
            rain = env.rain_intensity
            if rain > 0:
                wet_penalty = (rain / 100.0) * 20.0 # Up to 20s loss purely from water
                env_impact += wet_penalty
                
                # Tyre Compound Check (CRITICAL)
                if setup.tyres:
                    compound = setup.tyres.compound
                    if "slick" in compound:
                        # Slicks on wet track = Suicide
                        # Exponential penalty based on rain intensity
                        wrong_tyre_pen = (rain / 10.0) ** 2  # 10% rain = 1s, 50% rain = 25s, 100% = 100s
                        env_impact += wrong_tyre_pen
                    elif "wet" in compound:
                        # Wets on dry track = Overheating/Slow
                        if rain < 10: env_impact += 3.0
                        else: env_impact -= 2.0 # Wets working well


        current_time += env_impact

        return round(current_time, 3)

    def _calculate_setup_impact(self, s: EngineeringSetup, p: dict) -> float:
        """Calculates time delta based on physical engineering parameters"""
        delta = 0.0
        
        # --- AERO ---
        # More Wing = More Drag (Slower) but More Grip (Faster cornering)
        # Optimal for "Avg Track" is 6 Front / 7 Rear
        # Drag penalty is steeper than Downforce gain usually
        aero_drag = (s.aero.front_wing + s.aero.rear_wing) * 0.05 # +0.05s per click (Drag)
        aero_grip = (s.aero.front_wing + s.aero.rear_wing) * 0.08 # -0.08s per click (Cornering)
        
        # Balance: If Front and Rear are too far apart -> Understeer/Oversteer penalty
        balance_dev = abs(s.aero.front_wing - s.aero.rear_wing)
        if balance_dev > 4: delta += 0.5 # Unstable car penalty
        
        delta += (aero_drag - aero_grip)

        # --- SUSPENSION (Geometry) ---
        # Camber: Ideal -3.5F / -2.0R
        camber_pen = abs(s.suspension.camber_fl - (-3.5)) + abs(s.suspension.camber_rl - (-2.0))
        delta += camber_pen * 0.1

        # Ride Height: Lower is better for CG and Aero, UNTIL you hit the floor
        # Floor threshold approx 50mm
        avg_rh = (s.suspension.ride_height_f + s.suspension.ride_height_r) / 2
        if avg_rh < 50:
            delta += 1.0 # Bottoming out severely
        elif avg_rh < 60:
            delta -= 0.3 # Ground effect bonus
        else:
            delta += (avg_rh - 60) * 0.02 # Higher CG penalty

        # --- GEARBOX ---
        # Final Ratio: Higher (4.0) = Accel, Lower (3.2) = Top Speed
        # Ideal depends on track, lets say 3.8 is baseline.
        # 4.2 -> Top out early on straight (+ time)
        # 3.2 -> Slow accel out of corners (+ time)
        final = s.drivetrain.gear_ratio_final
        if final > 4.0: delta += 0.4 # Rev limiter hit
        elif final < 3.4: delta += 0.3 # Bogging down
        else: delta -= 0.1 # Good zone

        # --- BRAKES ---
        # Pressure: >95% risks lockups
        if s.brakes.pressure > 95: delta += 0.5 # Flat spots/Lockups
        # Bias: Needs to be ~54%
        if abs(s.brakes.bias - 54.0) > 4.0: delta += 0.4 # Unstable braking

        # --- PRESSURE (Tyres) ---
        # Ideal 24.5 psi hot
        p_dev = abs(s.tyres.pressure_fl - 24.5) + abs(s.tyres.pressure_rl - 23.5)
        delta += p_dev * 0.1

        return delta

    def analyze_telemetry(self, lap, best_sectors):
        msgs = []
        
        # 1. Fuel Strategy
        if lap.fuel_remaining < 3.0: msgs.append("CRITICAL FUEL: BOX NOW")
        elif lap.fuel_remaining < 10.0: msgs.append("FUEL LOW")

        # 2. Tyre Health
        if lap.tyre_wear > 0.85: msgs.append("PUNCTURE RISK")
        elif lap.tyre_wear > 0.6: msgs.append("TYRES DYING")
        
        # 3. Setup Feedback (The "Engineer" Voice)
        # If lap time is poor, give setup advice
        if lap.current_setup:
            s = lap.current_setup
            if s.brakes.pressure > 95: msgs.append("BRAKE LOCKING DETECTED")
            if s.drivetrain.gear_ratio_final > 4.1: msgs.append("HITTING LIMITER ON STRAIGHT")
            if (s.suspension.ride_height_f + s.suspension.ride_height_r)/2 < 50: msgs.append("BOTTOMING OUT HEAVILY")
            if abs(s.tyres.pressure_fl - 24.5) > 3.0: msgs.append("CHECK TYRE PRESSURES")

        if not msgs:
            # Random encouragement or Sector analysis
            msgs.append("PACE IS GOOD")
            
        return " | ".join(msgs)