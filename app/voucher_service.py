import uuid
from datetime import datetime
from typing import Dict, Any

from app.config import RISK_LEVELS


def generate_voucher_code(project_id: str) -> str:
    """生成凭证编号"""
    date_str = datetime.now().strftime('%Y%m%d')
    uid = uuid.uuid4().hex[:8].upper()
    return f"FW-{project_id[:8]}-{date_str}-{uid}"


def generate_conclusion(task_data, results, overall) -> str:
    """生成验算结论文本"""
    risk_cn = RISK_LEVELS.get(overall['overall_risk_level'], overall['overall_risk_level'])

    lines = []
    lines.append(f"【模板支撑验算结论】")
    lines.append(f"项目：{task_data.project_name}")
    lines.append(f"部位：{task_data.building}号楼 {task_data.floor}层 {task_data.location}")
    lines.append(f"构件类型：{task_data.element_type}")
    lines.append(f"支架高度：{task_data.support_height}m")
    lines.append(f"")
    lines.append(f"一、总体结论")
    lines.append(f"  风险等级：{risk_cn}")
    if overall['pass_status'] == 'pass':
        lines.append(f"  结论：验算通过，满足安全要求")
    elif overall['pass_status'] == 'warning':
        lines.append(f"  结论：存在一定风险，建议采取加强措施后使用")
    else:
        lines.append(f"  结论：验算不通过，不得使用")
    lines.append(f"  最大荷载比：{overall['max_ratio']:.3f}")
    lines.append(f"")
    lines.append(f"二、分项验算结果")

    passed_count = 0
    for r in results:
        status = "✓ 通过" if r['is_passed'] else "✗ 不通过"
        lines.append(f"  {r['check_item_name']}：{r['calculated_value']:.3f} / {r['allowable_value']:.3f} = {r['ratio']:.3f} {status}")
        if r['is_passed']:
            passed_count += 1

    lines.append(f"")
    lines.append(f"  共 {len(results)} 项验算，通过 {passed_count} 项，不通过 {len(results) - passed_count} 项")

    if overall['failure_reasons']:
        lines.append(f"")
        lines.append(f"三、不通过原因")
        for i, reason in enumerate(overall['failure_reasons'], 1):
            lines.append(f"  {i}. {reason}")

    lines.append(f"")
    lines.append(f"四、主要参数")
    lines.append(f"  面板：{task_data.panel_material} {task_data.panel_thickness}mm")
    lines.append(f"  次楞：{task_data.secondary_beam_material} {task_data.secondary_beam_size} @ {task_data.secondary_beam_spacing}mm")
    lines.append(f"  主楞：{task_data.main_beam_material} {task_data.main_beam_size} @ {task_data.main_beam_spacing}mm")
    lines.append(f"  立杆：{task_data.pole_type}")
    lines.append(f"  立杆间距：{task_data.pole_spacing_transverse}mm × {task_data.pole_spacing_longitudinal}mm")
    lines.append(f"  水平杆步距：{task_data.horizontal_step}mm")

    lines.append(f"")
    lines.append(f"验算时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"（本结论依据《混凝土结构工程施工规范》GB50666-2011、《建筑施工模板安全技术规范》JGJ162-2008等标准计算）")

    return "\n".join(lines)


def build_voucher_input(task_data) -> Dict[str, Any]:
    """构建输入参数快照"""
    return {
        'project_id': task_data.project_id,
        'project_name': task_data.project_name,
        'building': task_data.building,
        'floor': task_data.floor,
        'location': task_data.location,
        'element_type': task_data.element_type,
        'formwork_type': task_data.formwork_type,
        'support_height': task_data.support_height,
        'element_length': task_data.element_length,
        'element_width': task_data.element_width,
        'element_height': task_data.element_height,
        'slab_thickness': task_data.slab_thickness,
        'panel_material': task_data.panel_material,
        'panel_thickness': task_data.panel_thickness,
        'secondary_beam_material': task_data.secondary_beam_material,
        'secondary_beam_size': task_data.secondary_beam_size,
        'secondary_beam_spacing': task_data.secondary_beam_spacing,
        'main_beam_material': task_data.main_beam_material,
        'main_beam_size': task_data.main_beam_size,
        'main_beam_spacing': task_data.main_beam_spacing,
        'pole_type': task_data.pole_type,
        'pole_spacing_transverse': task_data.pole_spacing_transverse,
        'pole_spacing_longitudinal': task_data.pole_spacing_longitudinal,
        'horizontal_step': task_data.horizontal_step,
        'construction_load': task_data.construction_load
    }
