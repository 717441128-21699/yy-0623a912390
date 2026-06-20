import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.schemas import FormworkCheckCreate
from app.validator import validate_formwork_params, group_missing_params
from app.calculator import run_formwork_check
from app.voucher_service import generate_conclusion, build_voucher_input, generate_voucher_code


def test_validation_incomplete():
    print("=" * 60)
    print("测试1：参数完整性校验（楼板缺板厚）")
    print("=" * 60)

    data = FormworkCheckCreate(
        project_id="PRJ001",
        project_name="测试项目",
        building="1",
        floor="2",
        location="测试部位",
        element_type="slab",
        formwork_type="木模板",
        support_height=3.0,
        panel_material="plywood_15",
        panel_thickness=15,
        secondary_beam_material="wood_pine",
        secondary_beam_size="50x100",
        secondary_beam_spacing=250,
        main_beam_material="wood_pine",
        main_beam_size="50x100",
        main_beam_spacing=900,
        pole_type="steel_48x35",
        pole_spacing_transverse=900,
        pole_spacing_longitudinal=900,
        horizontal_step=1500
    )

    is_valid, missing_params = validate_formwork_params(data)

    print(f"校验结果: {'通过' if is_valid else '不通过'}")
    print(f"缺失参数数量: {len(missing_params)}")

    if missing_params:
        grouped = group_missing_params(missing_params)
        print("\n缺失参数分类:")
        for category, fields in grouped.items():
            print(f"  [{category}]: {', '.join(fields)}")

    print()
    return not is_valid


def test_validation_beam_incomplete():
    print("=" * 60)
    print("测试2：参数完整性校验（梁缺梁高）")
    print("=" * 60)

    data = FormworkCheckCreate(
        project_id="PRJ001",
        project_name="测试项目",
        building="1",
        floor="2",
        location="测试梁",
        element_type="beam",
        formwork_type="木模板",
        support_height=3.0,
        element_width=300,
        panel_material="plywood_15",
        panel_thickness=15,
        secondary_beam_material="wood_pine",
        secondary_beam_size="50x100",
        secondary_beam_spacing=200,
        main_beam_material="wood_pine",
        main_beam_size="50x100",
        main_beam_spacing=600,
        pole_type="steel_48x35",
        pole_spacing_transverse=600,
        pole_spacing_longitudinal=900,
        horizontal_step=1500
    )

    is_valid, missing_params = validate_formwork_params(data)

    print(f"校验结果: {'通过' if is_valid else '不通过'}")
    print(f"缺失参数数量: {len(missing_params)}")

    if missing_params:
        grouped = group_missing_params(missing_params)
        print("\n缺失参数分类:")
        for category, fields in grouped.items():
            print(f"  [{category}]: {', '.join(fields)}")

    print()
    return not is_valid


def test_slab_calculation():
    print("=" * 60)
    print("测试3：楼板模板支撑验算")
    print("=" * 60)

    data = FormworkCheckCreate(
        project_id="PRJ2024001",
        project_name="阳光花园住宅小区",
        building="3",
        floor="5",
        location="3号楼5层顶板东侧",
        element_type="slab",
        formwork_type="木模板",
        support_height=3.2,
        slab_thickness=120,
        panel_material="plywood_15",
        panel_thickness=15,
        secondary_beam_material="wood_pine",
        secondary_beam_size="50x100",
        secondary_beam_spacing=250,
        main_beam_material="wood_pine",
        main_beam_size="50x100",
        main_beam_spacing=900,
        pole_type="steel_48x35",
        pole_spacing_transverse=900,
        pole_spacing_longitudinal=900,
        horizontal_step=1500,
        construction_load=2.0,
        submitted_by="张工",
        remark="标准层楼板模板支撑验算"
    )

    is_valid, missing_params = validate_formwork_params(data)
    print(f"参数校验: {'通过' if is_valid else '不通过'}")

    if not is_valid:
        print(f"缺失参数: {missing_params}")
        return False

    result = run_formwork_check(data)

    print(f"\n荷载计算:")
    loads = result['loads']
    print(f"  永久荷载: {loads.get('permanent_load_kN_m2', 'N/A'):.2f} kN/m²")
    print(f"  可变荷载: {loads.get('variable_load_kN_m2', 'N/A'):.2f} kN/m²")
    print(f"  基本组合: {loads.get('basic_combination_kN_m2', 'N/A'):.2f} kN/m²")

    print(f"\n整体结论:")
    overall = result['overall']
    print(f"  风险等级: {overall['overall_risk_level']}")
    print(f"  通过状态: {overall['pass_status']}")
    print(f"  最大荷载比: {overall['max_ratio']:.3f}")
    print(f"  全部通过: {overall['all_passed']}")

    if overall['failure_reasons']:
        print(f"\n不通过原因:")
        for reason in overall['failure_reasons']:
            print(f"  - {reason}")

    print(f"\n分项结果:")
    for r in result['results']:
        status = "✓ 通过" if r['is_passed'] else "✗ 不通过"
        print(f"  {r['check_item_name']}: {r['calculated_value']:.3f} / {r['allowable_value']:.3f} = {r['ratio']:.3f} {status}")

    print()

    voucher_code = generate_voucher_code(data.project_id)
    print(f"凭证编号: {voucher_code}")

    conclusion = generate_conclusion(data, result['results'], overall)
    print(f"\n验算结论文本预览 (前600字):")
    print(conclusion[:600] + "..." if len(conclusion) > 600 else conclusion)

    print()
    return True


def test_beam_calculation():
    print("=" * 60)
    print("测试4：梁模板支撑验算")
    print("=" * 60)

    data = FormworkCheckCreate(
        project_id="PRJ2024001",
        project_name="阳光花园住宅小区",
        building="3",
        floor="5",
        location="3号楼5层KL3梁",
        element_type="beam",
        formwork_type="木模板",
        support_height=3.2,
        element_width=300,
        element_height=600,
        panel_material="plywood_15",
        panel_thickness=15,
        secondary_beam_material="wood_pine",
        secondary_beam_size="50x100",
        secondary_beam_spacing=200,
        main_beam_material="wood_pine",
        main_beam_size="60x120",
        main_beam_spacing=600,
        pole_type="steel_48x35",
        pole_spacing_transverse=600,
        pole_spacing_longitudinal=900,
        horizontal_step=1500,
        construction_load=2.5,
        submitted_by="李工"
    )

    is_valid, missing_params = validate_formwork_params(data)
    print(f"参数校验: {'通过' if is_valid else '不通过'}")

    if not is_valid:
        print(f"缺失参数: {missing_params}")
        return False

    result = run_formwork_check(data)

    print(f"\n整体结论:")
    overall = result['overall']
    print(f"  风险等级: {overall['overall_risk_level']}")
    print(f"  通过状态: {overall['pass_status']}")
    print(f"  最大荷载比: {overall['max_ratio']:.3f}")

    print(f"\n分项结果:")
    for r in result['results']:
        status = "✓ 通过" if r['is_passed'] else "✗ 不通过"
        print(f"  {r['check_item_name']}: {r['calculated_value']:.3f} / {r['allowable_value']:.3f} = {r['ratio']:.3f} {status}")

    print()
    return True


def main():
    print("\n" + "=" * 60)
    print("模板支撑验算服务 - 功能测试")
    print("=" * 60 + "\n")

    tests = [
        ("参数完整性校验（楼板缺板厚）", test_validation_incomplete),
        ("参数完整性校验（梁缺梁高）", test_validation_beam_incomplete),
        ("楼板模板支撑验算", test_slab_calculation),
        ("梁模板支撑验算", test_beam_calculation),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✓ 测试通过: {name}\n")
                passed += 1
            else:
                print(f"✗ 测试失败: {name}\n")
                failed += 1
        except Exception as e:
            print(f"✗ 测试异常: {name}")
            print(f"  错误: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"测试总结: 通过 {passed} / {len(tests)}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
