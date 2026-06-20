import urllib.request
import json

BASE_URL = "http://127.0.0.1:8080"


def test_health():
    print("=" * 60)
    print("测试1：健康检查")
    print("=" * 60)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health") as resp:
            data = json.loads(resp.read().decode())
            print(f"状态: {data['status']}")
            print(f"服务: {data['service']}")
            print("✓ 测试通过\n")
            return True
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        return False


def test_submit_slab():
    print("=" * 60)
    print("测试2：提交楼板验算任务")
    print("=" * 60)
    try:
        with open("examples/slab_example.json", "r", encoding="utf-8") as f:
            body = f.read()

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/formwork-check",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"任务ID: {data['task_id']}")
            print(f"任务编号: {data['task_code']}")
            print(f"状态: {data['status']}")
            print(f"风险等级: {data['overall_risk_level']}")
            print(f"通过状态: {data['pass_status']}")
            if data['failure_reasons']:
                print(f"不通过原因: {len(data['failure_reasons'])} 项")
            print(f"分项结果数: {len(data['results'])}")

            print("\n分项结果:")
            for r in data['results']:
                status = "✓" if r['is_passed'] else "✗"
                print(f"  {status} {r['check_item_name']}: {r['ratio']:.3f}")

            print("✓ 测试通过\n")
            return data['task_id']
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"HTTP错误: {e.code}")
        print(f"响应: {err_body}")
        print("✗ 测试失败\n")
        return None
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        return None


def test_get_task(task_id):
    print("=" * 60)
    print("测试3：查询任务详情")
    print("=" * 60)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/formwork-check/{task_id}") as resp:
            data = json.loads(resp.read().decode())
            print(f"任务ID: {data['task_id']}")
            print(f"任务编号: {data['task_code']}")
            print(f"风险等级: {data['overall_risk_level']}")
            print(f"分项结果数: {len(data['results'])}")
            print("✓ 测试通过\n")
            return True
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        return False


def test_list_tasks():
    print("=" * 60)
    print("测试4：查询历史记录列表")
    print("=" * 60)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/formwork-tasks?project_id=PRJ2024001&page=1&page_size=10") as resp:
            data = json.loads(resp.read().decode())
            print(f"总数: {data['total']}")
            print(f"当前页数量: {len(data['items'])}")
            if data['items']:
                item = data['items'][0]
                print(f"第一条: {item['task_code']} - {item['location']}")
            print("✓ 测试通过\n")
            return True
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        return False


def test_validation_error():
    print("=" * 60)
    print("测试5：参数不完整时的错误提示")
    print("=" * 60)
    try:
        incomplete_data = {
            "project_id": "PRJTEST001",
            "project_name": "测试项目",
            "building": "1",
            "floor": "1",
            "location": "测试部位",
            "element_type": "slab",
            "formwork_type": "木模板",
            "support_height": 3.0,
            "panel_material": "plywood_15",
            "panel_thickness": 15,
            "secondary_beam_material": "wood_pine",
            "secondary_beam_size": "50x100",
            "secondary_beam_spacing": 250,
            "main_beam_material": "wood_pine",
            "main_beam_size": "50x100",
            "main_beam_spacing": 900,
            "pole_type": "steel_48x35",
            "pole_spacing_transverse": 900,
            "pole_spacing_longitudinal": 900,
            "horizontal_step": 1500
        }

        body = json.dumps(incomplete_data, ensure_ascii=False)
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/formwork-check",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print("✗ 应该返回400错误，但返回了200\n")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 400:
            err_body = json.loads(e.read().decode())
            detail = err_body['detail']
            print(f"HTTP状态码: {e.code}")
            print(f"错误代码: {detail['code']}")
            print(f"错误信息: {detail['message']}")
            print(f"缺失参数数量: {len(detail['missing_params'])}")
            print("\n缺失参数列表:")
            for p in detail['missing_params']:
                print(f"  [{p['category']}] {p['name']} ({p['field']})")
            print("✓ 测试通过\n")
            return True
        else:
            print(f"HTTP错误: {e.code}")
            print("✗ 测试失败\n")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        return False


def test_get_voucher(task_id):
    print("=" * 60)
    print("测试6：获取计算凭证")
    print("=" * 60)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/formwork-voucher/{task_id}") as resp:
            data = json.loads(resp.read().decode())
            print(f"凭证编号: {data['voucher_code']}")
            print(f"创建时间: {data['created_at']}")
            print(f"输入参数字段数: {len(data['input_params'])}")
            print(f"计算步骤数: {len(data['calculation_process'])}")
            print(f"\n结论文本预览 (前300字):")
            print(data['conclusion'][:300] + "..." if len(data['conclusion']) > 300 else data['conclusion'])
            print("✓ 测试通过\n")
            return True
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        return False


def main():
    print("\n" + "=" * 60)
    print("模板支撑验算服务 - API接口测试")
    print("=" * 60 + "\n")

    task_id = None

    tests = [
        ("健康检查", lambda: test_health()),
    ]

    for name, test_func in tests:
        test_func()

    task_id = test_submit_slab()

    if task_id:
        test_get_task(task_id)
        test_get_voucher(task_id)

    test_list_tasks()
    test_validation_error()

    print("=" * 60)
    print("API测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
