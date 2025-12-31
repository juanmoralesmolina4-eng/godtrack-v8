from pydantic import BaseModel
from typing import List, Optional, Dict

# --- Granular Geometry & Mechanical ---
class SuspensionGeo(BaseModel):
    camber_fl: float = -3.5
    camber_fr: float = -3.5
    camber_rl: float = -2.0
    camber_rr: float = -2.0
    toe_front: float = -0.1
    toe_rear: float = 0.2
    caster: float = 12.0
    ride_height_f: float = 55.0
    ride_height_r: float = 60.0
    arb_f: int = 5
    arb_r: int = 5
    spring_f: int = 150000
    spring_r: int = 130000

class Dampers(BaseModel):
    bump_fl: int = 5
    bump_fr: int = 5
    bump_rl: int = 5
    bump_rr: int = 5
    rebound_fl: int = 5
    rebound_fr: int = 5
    rebound_rl: int = 5
    rebound_rr: int = 5

class Aerodynamics(BaseModel):
    front_wing: int = 5
    rear_wing: int = 5
    splitter_map: int = 5
    brake_ducts: int = 3

class Drivetrain(BaseModel):
    diff_preload: int = 50
    diff_accel: int = 50
    diff_coast: int = 40
    gear_ratio_final: float = 3.8
    gear_1: float = 3.2
    gear_2: float = 2.4
    gear_3: float = 1.9
    gear_4: float = 1.5
    gear_5: float = 1.2
    gear_6: float = 1.0
    gear_7: float = 0.9
    gear_8: float = 0.8

class Brakes(BaseModel):
    bias: float = 54.0
    pressure: float = 90.0
    disc_size_f: int = 320
    disc_size_r: int = 280
    pad_compound: int = 2

class Electronics(BaseModel):
    tc_level: int = 2
    abs_level: int = 4
    engine_map: int = 1
    throttle_shape: int = 5

class Tyres(BaseModel):
    compound: str = "slick_med"
    pressure_fl: float = 24.5
    pressure_fr: float = 24.5
    pressure_rl: float = 23.5
    pressure_rr: float = 23.5

class TrackEnvironment(BaseModel):
    air_temp: float = 25.0
    track_temp: float = 35.0
    grip_level: float = 0.95
    wind_speed: float = 10.0
    wind_direction: str = "N"
    rain_intensity: float = 0.0 # 0-100%

# --- Composite Engineering Setup ---
class EngineeringSetup(BaseModel):
    aero: Aerodynamics = Aerodynamics()
    suspension: SuspensionGeo = SuspensionGeo()
    dampers: Dampers = Dampers()
    drivetrain: Drivetrain = Drivetrain()
    electronics: Electronics = Electronics()
    tyres: Tyres = Tyres()
    brakes: Brakes = Brakes()
    environment: TrackEnvironment = TrackEnvironment()

# --- General Models ---
class LapInput(BaseModel):
    lap_time: float
    s1: float
    s2: float
    s3: float
    fuel_remaining: float
    tyre_wear: float
    is_pit_stop: bool
    is_sc: bool = False
    weather_cond: str = "dry"
    air_temp: float = 22.0

class SimulationInput(BaseModel):
    car_class: str
    initial_fuel: float
    laps_to_simulate: int
    pit_stop_lap: Optional[int] = None
    tyre_compound: str = "med"

class SimulationResult(BaseModel):
    lap: int
    estimated_time: float
    fuel_remaining: float
    tyre_wear: float
    message: str

class Profile(BaseModel):
    name: str
    car_class: str
    track: str
    setup: EngineeringSetup

class SessionStatus(BaseModel):
    current_lap: int
    last_lap_time: float
    s1: float
    s2: float
    s3: float
    fuel: float
    tyre_wear: float
    engineer_message: str
    best_lap: float
    best_s1: float
    best_s2: float
    best_s3: float
    theoretical_lap: float
    current_setup: EngineeringSetup
    delta_to_best: float = 0.0
    est_laps_remaining: float = 0.0