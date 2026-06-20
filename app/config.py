import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(PROJECT_ROOT, 'formwork_check.db')}")

API_V1_PREFIX = "/api/v1"

RISK_LEVELS = {
    "safe": "安全",
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "重大风险"
}

CHECK_ITEMS = [
    "panel_bending",
    "panel_shear",
    "panel_deflection",
    "secondary_beam_bending",
    "secondary_beam_shear",
    "secondary_beam_deflection",
    "main_beam_bending",
    "main_beam_shear",
    "main_beam_deflection",
    "pole_stability",
    "pole_compression",
    "foundation_bearing"
]

MATERIAL_PROPERTIES = {
    "wood_pine": {
        "name": "松木",
        "E": 9000,
        "f_m": 13,
        "f_v": 1.4,
        "f_c": 10,
        "unit_weight": 5
    },
    "wood_fir": {
        "name": "杉木",
        "E": 9000,
        "f_m": 11,
        "f_v": 1.2,
        "f_c": 10,
        "unit_weight": 4
    },
    "steel_q235": {
        "name": "Q235钢",
        "E": 206000,
        "f": 215,
        "f_v": 125,
        "unit_weight": 78.5
    },
    "steel_q355": {
        "name": "Q355钢",
        "E": 206000,
        "f": 305,
        "f_v": 175,
        "unit_weight": 78.5
    },
    "bamboo": {
        "name": "竹胶板",
        "E": 8000,
        "f_m": 80,
        "f_v": 8,
        "f_c": 60,
        "unit_weight": 7
    },
    "plywood_15": {
        "name": "15mm木胶合板",
        "E": 6000,
        "f_m": 25,
        "f_v": 2.5,
        "f_c": 25,
        "unit_weight": 6
    },
    "plywood_18": {
        "name": "18mm木胶合板",
        "E": 6000,
        "f_m": 25,
        "f_v": 2.5,
        "f_c": 25,
        "unit_weight": 7.2
    }
}

POLE_TYPES = {
    "steel_48x30": {
        "name": "Φ48×3.0钢管",
        "outer_diameter": 48,
        "thickness": 3.0,
        "area": 4.24,
        "moment_of_inertia": 10.78,
        "section_modulus": 4.49,
        "radius_of_gyration": 1.59,
        "weight_per_meter": 3.33
    },
    "steel_48x35": {
        "name": "Φ48×3.5钢管",
        "outer_diameter": 48,
        "thickness": 3.5,
        "area": 4.89,
        "moment_of_inertia": 12.19,
        "section_modulus": 5.08,
        "radius_of_gyration": 1.58,
        "weight_per_meter": 3.84
    },
    "steel_60x32": {
        "name": "Φ60×3.2钢管",
        "outer_diameter": 60,
        "thickness": 3.2,
        "area": 5.70,
        "moment_of_inertia": 23.02,
        "section_modulus": 7.67,
        "radius_of_gyration": 2.01,
        "weight_per_meter": 4.47
    }
}

CONCRETE_UNIT_WEIGHT = 24
REBAR_UNIT_WEIGHT = 1.1
CONSTRUCTION_LIVE_LOAD_SLAB = 2.0
CONSTRUCTION_LIVE_LOAD_BEAM = 2.5
VIBRATION_LOAD_SLAB = 1.0
VIBRATION_LOAD_BEAM = 2.0
