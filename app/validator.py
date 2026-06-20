from typing import List, Dict, Tuple
from app.schemas import FormworkCheckCreate


def validate_formwork_params(data: FormworkCheckCreate) -> Tuple[bool, List[Dict[str, str]]]:
    missing_params = []

    base_required = [
        ('project_id', '项目ID', '基础信息'),
        ('project_name', '项目名称', '基础信息'),
        ('building', '楼栋号', '基础信息'),
        ('floor', '楼层', '基础信息'),
        ('location', '工程部位', '基础信息'),
        ('element_type', '构件类型', '基础信息'),
        ('formwork_type', '模板类型', '基础信息'),
        ('support_height', '支架高度', '几何参数'),
    ]

    for field, name, category in base_required:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_params.append({
                'field': field,
                'name': name,
                'category': category
            })

    if data.element_type == 'slab':
        slab_required = [
            ('slab_thickness', '板厚', '几何参数'),
        ]
        for field, name, category in slab_required:
            value = getattr(data, field)
            if value is None or value <= 0:
                missing_params.append({
                    'field': field,
                    'name': name,
                    'category': category
                })
    elif data.element_type == 'beam':
        beam_required = [
            ('element_width', '梁宽', '几何参数'),
            ('element_height', '梁高', '几何参数'),
        ]
        for field, name, category in beam_required:
            value = getattr(data, field)
            if value is None or value <= 0:
                missing_params.append({
                    'field': field,
                    'name': name,
                    'category': category
                })
    elif data.element_type == 'column':
        column_required = [
            ('element_width', '柱宽', '几何参数'),
            ('element_length', '柱长', '几何参数'),
        ]
        for field, name, category in column_required:
            value = getattr(data, field)
            if value is None or value <= 0:
                missing_params.append({
                    'field': field,
                    'name': name,
                    'category': category
                })
    elif data.element_type == 'wall':
        wall_required = [
            ('element_height', '墙高', '几何参数'),
            ('slab_thickness', '墙厚', '几何参数'),
        ]
        for field, name, category in wall_required:
            value = getattr(data, field)
            if value is None or value <= 0:
                missing_params.append({
                    'field': field,
                    'name': name,
                    'category': category
                })

    panel_required = [
        ('panel_material', '面板材料', '材料参数'),
        ('panel_thickness', '面板厚度', '材料参数'),
    ]
    for field, name, category in panel_required:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (int, float)) and value <= 0):
            missing_params.append({
                'field': field,
                'name': name,
                'category': category
            })

    secondary_beam_required = [
        ('secondary_beam_material', '次楞材料', '楞梁参数'),
        ('secondary_beam_size', '次楞规格', '楞梁参数'),
        ('secondary_beam_spacing', '次楞间距', '楞梁参数'),
    ]
    for field, name, category in secondary_beam_required:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (int, float)) and value <= 0):
            missing_params.append({
                'field': field,
                'name': name,
                'category': category
            })

    main_beam_required = [
        ('main_beam_material', '主楞材料', '楞梁参数'),
        ('main_beam_size', '主楞规格', '楞梁参数'),
        ('main_beam_spacing', '主楞间距', '楞梁参数'),
    ]
    for field, name, category in main_beam_required:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (int, float)) and value <= 0):
            missing_params.append({
                'field': field,
                'name': name,
                'category': category
            })

    pole_required = [
        ('pole_type', '立杆类型', '支架参数'),
        ('pole_spacing_transverse', '立杆横距', '支架参数'),
        ('pole_spacing_longitudinal', '立杆纵距', '支架参数'),
        ('horizontal_step', '水平杆步距', '支架参数'),
    ]
    for field, name, category in pole_required:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (int, float)) and value <= 0):
            missing_params.append({
                'field': field,
                'name': name,
                'category': category
            })

    return len(missing_params) == 0, missing_params


def group_missing_params(missing_params: List[Dict[str, str]]) -> Dict[str, List[str]]:
    grouped = {}
    for item in missing_params:
        category = item['category']
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(item['name'])
    return grouped
