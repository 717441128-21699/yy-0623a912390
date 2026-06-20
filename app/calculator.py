import math
from typing import Dict, Any, Tuple, List
from app.config import (
    MATERIAL_PROPERTIES,
    POLE_TYPES,
    CONCRETE_UNIT_WEIGHT,
    REBAR_UNIT_WEIGHT,
    CONSTRUCTION_LIVE_LOAD_SLAB,
    CONSTRUCTION_LIVE_LOAD_BEAM,
    VIBRATION_LOAD_SLAB,
    VIBRATION_LOAD_BEAM
)


def get_material_property(material_key: str) -> Dict[str, Any]:
    return MATERIAL_PROPERTIES.get(material_key, MATERIAL_PROPERTIES['wood_pine'])


def get_pole_property(pole_key: str) -> Dict[str, Any]:
    return POLE_TYPES.get(pole_key, POLE_TYPES['steel_48x35'])


def parse_beam_size(size_str: str) -> Tuple[float, float]:
    size_str = size_str.strip().lower().replace('×', 'x').replace('*', 'x')
    if 'x' in size_str:
        parts = size_str.split('x')
        try:
            b = float(parts[0].strip())
            h = float(parts[1].strip())
            return b, h
        except (ValueError, IndexError):
            return 50.0, 100.0
    return 50.0, 100.0


def calculate_section_properties(b: float, h: float) -> Dict[str, float]:
    I = b * h ** 3 / 12
    W = b * h ** 2 / 6
    S = b * h / 2
    A = b * h
    return {'I': I, 'W': W, 'S': S, 'A': A}


def calculate_loads(data) -> Dict[str, Any]:
    loads = {}

    if data.element_type == 'slab':
        slab_h_m = data.slab_thickness / 1000.0
        G1k = CONCRETE_UNIT_WEIGHT * slab_h_m
        G2k = REBAR_UNIT_WEIGHT * slab_h_m
        G3k = 0.3
        Q1k = data.construction_load if data.construction_load else CONSTRUCTION_LIVE_LOAD_SLAB
        Q2k = VIBRATION_LOAD_SLAB

        Gk = G1k + G2k + G3k
        Qk = Q1k + Q2k

        loads['concrete_weight_kN_m2'] = G1k
        loads['rebar_weight_kN_m2'] = G2k
        loads['formwork_weight_kN_m2'] = G3k
        loads['construction_load_kN_m2'] = Q1k
        loads['vibration_load_kN_m2'] = Q2k
        loads['permanent_load_kN_m2'] = Gk
        loads['variable_load_kN_m2'] = Qk
        loads['basic_combination_kN_m2'] = 1.2 * Gk + 1.4 * Qk
        loads['deflection_combination_kN_m2'] = Gk + Qk

    elif data.element_type == 'beam':
        beam_w_m = data.element_width / 1000.0
        beam_h_m = data.element_height / 1000.0
        G1k = CONCRETE_UNIT_WEIGHT * beam_h_m
        G2k = REBAR_UNIT_WEIGHT * beam_h_m
        G3k = 0.5
        Q1k = data.construction_load if data.construction_load else CONSTRUCTION_LIVE_LOAD_BEAM
        Q2k = VIBRATION_LOAD_BEAM

        Gk = G1k + G2k + G3k
        Qk = Q1k + Q2k

        loads['beam_width_m'] = beam_w_m
        loads['beam_height_m'] = beam_h_m
        loads['concrete_weight_kN_m2'] = G1k
        loads['rebar_weight_kN_m2'] = G2k
        loads['formwork_weight_kN_m2'] = G3k
        loads['construction_load_kN_m2'] = Q1k
        loads['vibration_load_kN_m2'] = Q2k
        loads['permanent_load_line_kN_m'] = Gk * beam_w_m
        loads['variable_load_line_kN_m'] = Qk * beam_w_m
        loads['basic_combination_line_kN_m'] = (1.2 * Gk + 1.4 * Qk) * beam_w_m
        loads['deflection_combination_line_kN_m'] = (Gk + Qk) * beam_w_m

    else:
        loads = calculate_default_loads(data)

    return loads


def calculate_default_loads(data) -> Dict[str, Any]:
    Gk = 5.0
    Qk = 2.5
    return {
        'permanent_load_kN_m2': Gk,
        'variable_load_kN_m2': Qk,
        'basic_combination_kN_m2': 1.2 * Gk + 1.4 * Qk,
        'deflection_combination_kN_m2': Gk + Qk
    }


def _line_load_kN_m_to_N_mm(q_kN_m: float) -> float:
    return q_kN_m * 1000 / 1000


def check_panel(data, loads: Dict[str, Any]) -> Dict[str, Any]:
    results = {}

    mat = get_material_property(data.panel_material)
    t_mm = data.panel_thickness
    l_mm = data.secondary_beam_spacing

    b_mm = 1000.0
    sec = calculate_section_properties(b_mm, t_mm)

    if data.element_type == 'slab':
        q_design_kN_m2 = loads['basic_combination_kN_m2']
        q_deflect_kN_m2 = loads['deflection_combination_kN_m2']
        q_kN_m = q_design_kN_m2 * (b_mm / 1000)
        q_deflect_kN_m = q_deflect_kN_m2 * (b_mm / 1000)
    elif data.element_type == 'beam':
        q_kN_m = loads.get('basic_combination_line_kN_m', 10.0)
        q_deflect_kN_m = loads.get('deflection_combination_line_kN_m', 8.0)
    else:
        q_kN_m = 10.0
        q_deflect_kN_m = 8.0

    q_N_mm = _line_load_kN_m_to_N_mm(q_kN_m)
    q_deflect_N_mm = _line_load_kN_m_to_N_mm(q_deflect_kN_m)

    l_m = l_mm / 1000.0
    M_max_kN_m = q_kN_m * l_m ** 2 / 8
    V_max_kN = q_kN_m * l_m / 2

    sigma_m_N_mm2 = M_max_kN_m * 1e6 / sec['W']
    f_m_N_mm2 = mat['f_m']
    bending_ratio = sigma_m_N_mm2 / f_m_N_mm2

    tau_N_mm2 = 1.5 * V_max_kN * 1000 / sec['A']
    f_v_N_mm2 = mat['f_v']
    shear_ratio = tau_N_mm2 / f_v_N_mm2

    w_max_mm = 5 * q_deflect_N_mm * l_mm ** 4 / (384 * mat['E'] * sec['I'])
    w_allow_mm = l_mm / 250
    deflection_ratio = w_max_mm / w_allow_mm

    results['bending'] = {
        'check_item': 'panel_bending',
        'check_item_name': '面板抗弯强度',
        'calculated_value': round(sigma_m_N_mm2, 3),
        'allowable_value': f_m_N_mm2,
        'ratio': round(bending_ratio, 3),
        'is_passed': bending_ratio <= 1.0,
        'risk_level': get_risk_level(bending_ratio),
        'detail': {
            'max_moment_kN_m': round(M_max_kN_m, 4),
            'section_modulus_mm3': round(sec['W'], 2),
            'span_mm': l_mm,
            'design_load_kN_m': round(q_kN_m, 3),
            'unit': 'N/mm²'
        }
    }

    results['shear'] = {
        'check_item': 'panel_shear',
        'check_item_name': '面板抗剪强度',
        'calculated_value': round(tau_N_mm2, 3),
        'allowable_value': f_v_N_mm2,
        'ratio': round(shear_ratio, 3),
        'is_passed': shear_ratio <= 1.0,
        'risk_level': get_risk_level(shear_ratio),
        'detail': {
            'max_shear_kN': round(V_max_kN, 3),
            'section_area_mm2': round(sec['A'], 2),
            'span_mm': l_mm,
            'unit': 'N/mm²'
        }
    }

    results['deflection'] = {
        'check_item': 'panel_deflection',
        'check_item_name': '面板挠度',
        'calculated_value': round(w_max_mm, 3),
        'allowable_value': round(w_allow_mm, 3),
        'ratio': round(deflection_ratio, 3),
        'is_passed': deflection_ratio <= 1.0,
        'risk_level': get_risk_level(deflection_ratio),
        'detail': {
            'E_N_mm2': mat['E'],
            'I_mm4': sec['I'],
            'span_mm': l_mm,
            'deflection_load_kN_m': round(q_deflect_kN_m, 3),
            'allowable_l_250': l_mm / 250,
            'unit': 'mm'
        }
    }

    return results


def check_secondary_beam(data, loads: Dict[str, Any]) -> Dict[str, Any]:
    results = {}

    mat = get_material_property(data.secondary_beam_material)
    b_mm, h_mm = parse_beam_size(data.secondary_beam_size)
    sec = calculate_section_properties(b_mm, h_mm)
    l_mm = data.main_beam_spacing
    spacing_mm = data.secondary_beam_spacing

    spacing_m = spacing_mm / 1000.0

    if data.element_type == 'slab':
        q_kN_m = loads['basic_combination_kN_m2'] * spacing_m
        q_deflect_kN_m = loads['deflection_combination_kN_m2'] * spacing_m
    elif data.element_type == 'beam':
        beam_w_m = data.element_width / 1000.0
        num_beams = max(1, math.ceil(beam_w_m / spacing_m))
        q_kN_m = loads['basic_combination_line_kN_m'] / num_beams
        q_deflect_kN_m = loads['deflection_combination_line_kN_m'] / num_beams
    else:
        q_kN_m = 5.0
        q_deflect_kN_m = 4.0

    q_N_mm = _line_load_kN_m_to_N_mm(q_kN_m)
    q_deflect_N_mm = _line_load_kN_m_to_N_mm(q_deflect_kN_m)

    l_m = l_mm / 1000.0
    M_max_kN_m = q_kN_m * l_m ** 2 / 8
    V_max_kN = q_kN_m * l_m / 2

    sigma_m_N_mm2 = M_max_kN_m * 1e6 / sec['W']
    f_m_N_mm2 = mat['f_m']
    bending_ratio = sigma_m_N_mm2 / f_m_N_mm2

    tau_N_mm2 = 1.5 * V_max_kN * 1000 / sec['A']
    f_v_N_mm2 = mat['f_v']
    shear_ratio = tau_N_mm2 / f_v_N_mm2

    w_max_mm = 5 * q_deflect_N_mm * l_mm ** 4 / (384 * mat['E'] * sec['I'])
    w_allow_mm = l_mm / 250
    deflection_ratio = w_max_mm / w_allow_mm

    results['bending'] = {
        'check_item': 'secondary_beam_bending',
        'check_item_name': '次楞抗弯强度',
        'calculated_value': round(sigma_m_N_mm2, 3),
        'allowable_value': f_m_N_mm2,
        'ratio': round(bending_ratio, 3),
        'is_passed': bending_ratio <= 1.0,
        'risk_level': get_risk_level(bending_ratio),
        'detail': {
            'max_moment_kN_m': round(M_max_kN_m, 4),
            'section_modulus_mm3': round(sec['W'], 2),
            'beam_size': f'{b_mm}x{h_mm}mm',
            'span_mm': l_mm,
            'spacing_mm': spacing_mm,
            'unit': 'N/mm²'
        }
    }

    results['shear'] = {
        'check_item': 'secondary_beam_shear',
        'check_item_name': '次楞抗剪强度',
        'calculated_value': round(tau_N_mm2, 3),
        'allowable_value': f_v_N_mm2,
        'ratio': round(shear_ratio, 3),
        'is_passed': shear_ratio <= 1.0,
        'risk_level': get_risk_level(shear_ratio),
        'detail': {
            'max_shear_kN': round(V_max_kN, 3),
            'section_area_mm2': round(sec['A'], 2),
            'span_mm': l_mm,
            'unit': 'N/mm²'
        }
    }

    results['deflection'] = {
        'check_item': 'secondary_beam_deflection',
        'check_item_name': '次楞挠度',
        'calculated_value': round(w_max_mm, 3),
        'allowable_value': round(w_allow_mm, 3),
        'ratio': round(deflection_ratio, 3),
        'is_passed': deflection_ratio <= 1.0,
        'risk_level': get_risk_level(deflection_ratio),
        'detail': {
            'E_N_mm2': mat['E'],
            'I_mm4': sec['I'],
            'span_mm': l_mm,
            'allowable_l_250': w_allow_mm,
            'unit': 'mm'
        }
    }

    return results


def check_main_beam(data, loads: Dict[str, Any]) -> Dict[str, Any]:
    results = {}

    mat = get_material_property(data.main_beam_material)
    b_mm, h_mm = parse_beam_size(data.main_beam_size)
    sec = calculate_section_properties(b_mm, h_mm)
    l_trans_mm = data.pole_spacing_transverse
    l_long_mm = data.pole_spacing_longitudinal
    secondary_spacing_mm = data.secondary_beam_spacing

    l_mm = min(l_trans_mm, l_long_mm)
    l_m = l_mm / 1000.0
    main_beam_spacing_m = data.main_beam_spacing / 1000.0

    if data.element_type == 'slab':
        load_area_m2 = l_m * main_beam_spacing_m
        total_load_kN = loads['basic_combination_kN_m2'] * load_area_m2
        q_kN_m = total_load_kN / l_m
        q_deflect_kN_m = loads['deflection_combination_kN_m2'] * load_area_m2 / l_m
    elif data.element_type == 'beam':
        total_load_kN = loads['basic_combination_line_kN_m'] * main_beam_spacing_m
        q_kN_m = total_load_kN / l_m
        q_deflect_kN_m = loads['deflection_combination_line_kN_m'] * main_beam_spacing_m / l_m
    else:
        q_kN_m = 8.0
        q_deflect_kN_m = 6.0

    q_N_mm = _line_load_kN_m_to_N_mm(q_kN_m)
    q_deflect_N_mm = _line_load_kN_m_to_N_mm(q_deflect_kN_m)

    M_max_kN_m = q_kN_m * l_m ** 2 / 8
    V_max_kN = q_kN_m * l_m / 2

    f_m_N_mm2 = mat.get('f_m', mat.get('f', 215))
    sigma_m_N_mm2 = M_max_kN_m * 1e6 / sec['W']
    bending_ratio = sigma_m_N_mm2 / f_m_N_mm2

    f_v_N_mm2 = mat.get('f_v', 125)
    tau_N_mm2 = 1.5 * V_max_kN * 1000 / sec['A']
    shear_ratio = tau_N_mm2 / f_v_N_mm2

    w_max_mm = 5 * q_deflect_N_mm * l_mm ** 4 / (384 * mat['E'] * sec['I'])
    w_allow_mm = l_mm / 400
    deflection_ratio = w_max_mm / w_allow_mm

    results['bending'] = {
        'check_item': 'main_beam_bending',
        'check_item_name': '主楞抗弯强度',
        'calculated_value': round(sigma_m_N_mm2, 3),
        'allowable_value': f_m_N_mm2,
        'ratio': round(bending_ratio, 3),
        'is_passed': bending_ratio <= 1.0,
        'risk_level': get_risk_level(bending_ratio),
        'detail': {
            'max_moment_kN_m': round(M_max_kN_m, 4),
            'section_modulus_mm3': round(sec['W'], 2),
            'beam_size': f'{b_mm}x{h_mm}mm',
            'span_mm': l_mm,
            'unit': 'N/mm²'
        }
    }

    results['shear'] = {
        'check_item': 'main_beam_shear',
        'check_item_name': '主楞抗剪强度',
        'calculated_value': round(tau_N_mm2, 3),
        'allowable_value': f_v_N_mm2,
        'ratio': round(shear_ratio, 3),
        'is_passed': shear_ratio <= 1.0,
        'risk_level': get_risk_level(shear_ratio),
        'detail': {
            'max_shear_kN': round(V_max_kN, 3),
            'section_area_mm2': round(sec['A'], 2),
            'span_mm': l_mm,
            'unit': 'N/mm²'
        }
    }

    results['deflection'] = {
        'check_item': 'main_beam_deflection',
        'check_item_name': '主楞挠度',
        'calculated_value': round(w_max_mm, 3),
        'allowable_value': round(w_allow_mm, 3),
        'ratio': round(deflection_ratio, 3),
        'is_passed': deflection_ratio <= 1.0,
        'risk_level': get_risk_level(deflection_ratio),
        'detail': {
            'E_N_mm2': mat['E'],
            'I_mm4': sec['I'],
            'span_mm': l_mm,
            'allowable_l_400': w_allow_mm,
            'unit': 'mm'
        }
    }

    return results


def check_pole_stability(data, loads: Dict[str, Any]) -> Dict[str, Any]:
    pole = get_pole_property(data.pole_type)
    H_m = data.support_height
    step_m = data.horizontal_step / 1000.0

    l_trans_m = data.pole_spacing_transverse / 1000.0
    l_long_m = data.pole_spacing_longitudinal / 1000.0

    load_area_m2 = l_trans_m * l_long_m

    if data.element_type == 'slab':
        N_design_kN = loads['basic_combination_kN_m2'] * load_area_m2
    elif data.element_type == 'beam':
        N_design_kN = loads['basic_combination_line_kN_m'] * (data.main_beam_spacing / 1000.0)
    else:
        N_design_kN = 20.0

    pole_weight_kN = pole['weight_per_meter'] * H_m * 9.8 / 1000.0
    N_total_kN = N_design_kN + pole_weight_kN

    L0_m = 1.155 * 1.5 * step_m
    i_cm = pole['radius_of_gyration']
    i_mm = i_cm * 10
    L0_mm = L0_m * 1000
    lambda_val = L0_mm / i_mm

    is_steel = 'steel' in data.pole_type or 'q235' in data.pole_type.lower() or 'q355' in data.pole_type.lower()

    if is_steel:
        phi = calculate_steel_stability_phi(lambda_val, 'a')
        if 'q355' in data.pole_type.lower():
            f_y_N_mm2 = 305
        else:
            f_y_N_mm2 = 215
    else:
        phi = calculate_wood_stability_phi(lambda_val)
        f_y_N_mm2 = 10

    A_cm2 = pole['area']
    A_mm2 = A_cm2 * 100

    sigma_N_mm2 = N_total_kN * 1000 / A_mm2
    sigma_design_N_mm2 = sigma_N_mm2 / phi if phi > 0 else 9999
    stability_ratio = sigma_design_N_mm2 / f_y_N_mm2

    sigma_compress_N_mm2 = N_total_kN * 1000 / A_mm2
    f_c_N_mm2 = f_y_N_mm2
    compression_ratio = sigma_compress_N_mm2 / f_c_N_mm2

    return {
        'stability': {
            'check_item': 'pole_stability',
            'check_item_name': '立杆稳定性',
            'calculated_value': round(sigma_design_N_mm2, 3),
            'allowable_value': f_y_N_mm2,
            'ratio': round(stability_ratio, 3),
            'is_passed': stability_ratio <= 1.0,
            'risk_level': get_risk_level(stability_ratio),
            'detail': {
                'axial_force_kN': round(N_total_kN, 3),
                'section_area_mm2': round(A_mm2, 2),
                'calculated_length_m': round(L0_m, 3),
                'slenderness_ratio': round(lambda_val, 2),
                'stability_coefficient': round(phi, 4),
                'support_height_m': H_m,
                'step_m': step_m,
                'unit': 'N/mm²'
            }
        },
        'compression': {
            'check_item': 'pole_compression',
            'check_item_name': '立杆抗压强度',
            'calculated_value': round(sigma_compress_N_mm2, 3),
            'allowable_value': f_c_N_mm2,
            'ratio': round(compression_ratio, 3),
            'is_passed': compression_ratio <= 1.0,
            'risk_level': get_risk_level(compression_ratio),
            'detail': {
                'axial_force_kN': round(N_total_kN, 3),
                'section_area_mm2': round(A_mm2, 2),
                'unit': 'N/mm²'
            }
        }
    }


def check_foundation(data, loads: Dict[str, Any]) -> Dict[str, Any]:
    l_trans_m = data.pole_spacing_transverse / 1000.0
    l_long_m = data.pole_spacing_longitudinal / 1000.0

    load_area_m2 = l_trans_m * l_long_m

    if data.element_type == 'slab':
        N_design_kN = loads['basic_combination_kN_m2'] * load_area_m2
    elif data.element_type == 'beam':
        N_design_kN = loads['basic_combination_line_kN_m'] * (data.main_beam_spacing / 1000.0)
    else:
        N_design_kN = 15.0

    base_width_m = 0.25
    base_area_m2 = base_width_m * base_width_m
    p_max_kPa = N_design_kN / base_area_m2

    f_a_kPa = 120.0

    bearing_ratio = p_max_kPa / f_a_kPa

    return {
        'bearing': {
            'check_item': 'foundation_bearing',
            'check_item_name': '地基承载力',
            'calculated_value': round(p_max_kPa, 2),
            'allowable_value': f_a_kPa,
            'ratio': round(bearing_ratio, 3),
            'is_passed': bearing_ratio <= 1.0,
            'risk_level': get_risk_level(bearing_ratio),
            'detail': {
                'axial_force_kN': round(N_design_kN, 3),
                'base_area_m2': round(base_area_m2, 4),
                'base_size': '250x250mm',
                'unit': 'kPa'
            }
        }
    }


def calculate_steel_stability_phi(lambda_val: float, section_class: str = 'a') -> float:
    if section_class == 'a':
        if lambda_val <= 100:
            phi = 1.0 - 0.002 * lambda_val
        else:
            phi = 8500 / (lambda_val ** 2)
    elif section_class == 'b':
        if lambda_val <= 100:
            phi = 1.0 - 0.003 * lambda_val
        else:
            phi = 7800 / (lambda_val ** 2)
    else:
        phi = 7000 / (lambda_val ** 2)
    return max(0.01, min(0.999, phi))


def calculate_wood_stability_phi(lambda_val: float) -> float:
    if lambda_val <= 75:
        phi = 1.0 - (lambda_val ** 2) / 2800
    else:
        phi = 3000 / (lambda_val ** 2)
    return max(0.01, min(0.999, phi))


def get_risk_level(ratio: float) -> str:
    if ratio <= 0.7:
        return 'safe'
    elif ratio <= 0.85:
        return 'low'
    elif ratio <= 0.95:
        return 'medium'
    elif ratio <= 1.0:
        return 'high'
    else:
        return 'critical'


def calculate_overall_risk(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_passed = all(r['is_passed'] for r in results)
    max_ratio = max(r['ratio'] for r in results)

    risk_level = get_risk_level(max_ratio)

    failure_reasons = []
    for r in results:
        if not r['is_passed']:
            failure_reasons.append(f"{r['check_item_name']}不满足要求：计算值{r['calculated_value']} > 允许值{r['allowable_value']}")

    if all_passed:
        pass_status = 'pass'
    elif max_ratio <= 1.1:
        pass_status = 'warning'
    else:
        pass_status = 'fail'

    return {
        'overall_risk_level': risk_level,
        'pass_status': pass_status,
        'failure_reasons': failure_reasons,
        'max_ratio': max_ratio,
        'all_passed': all_passed
    }


def run_formwork_check(data) -> Dict[str, Any]:
    loads = calculate_loads(data)

    panel_results = check_panel(data, loads)
    secondary_results = check_secondary_beam(data, loads)
    main_results = check_main_beam(data, loads)
    pole_results = check_pole_stability(data, loads)
    foundation_results = check_foundation(data, loads)

    all_results = []
    all_results.extend(panel_results.values())
    all_results.extend(secondary_results.values())
    all_results.extend(main_results.values())
    all_results.extend(pole_results.values())
    all_results.extend(foundation_results.values())

    overall = calculate_overall_risk(all_results)

    return {
        'loads': loads,
        'results': all_results,
        'overall': overall,
        'calculation_steps': {
            'load_calculation': loads,
            'panel_check': panel_results,
            'secondary_beam_check': secondary_results,
            'main_beam_check': main_results,
            'pole_check': pole_results,
            'foundation_check': foundation_results
        }
    }
