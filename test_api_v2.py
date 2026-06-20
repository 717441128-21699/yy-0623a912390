import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:8080"


def _post(path, body_dict):
    body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _get(path):
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_health():
    print("=" * 60)
    print("测试1：健康检查")
    print("=" * 60)
    status, data = _get("/health")
    print(f"状态码: {status}")
    print(f"响应: {data}")
    assert status == 200
    assert data['status'] == 'ok'
    print("✓ 通过\n")


def test_submit_single():
    print("=" * 60)
    print("测试2：单条提交验算任务")
    print("=" * 60)
    with open("examples/slab_example.json", "r", encoding="utf-8") as f:
        body = json.load(f)
    status, data = _post("/api/v1/formwork-check", body)
    print(f"状态码: {status}")
    print(f"任务ID: {data['task_id']}")
    print(f"风险等级: {data['overall_risk_level']}")
    print(f"通过状态: {data['pass_status']}")
    print(f"分项结果数: {len(data['results'])}")
    assert status == 200
    assert data['status'] == 'completed'
    print("✓ 通过\n")
    return data['task_id'], data['task_code']


def test_unified_validation_error():
    print("=" * 60)
    print("测试3：统一缺参数400错误格式")
    print("=" * 60)

    incomplete = {
        "project_id": "PRJTEST",
        "project_name": "测试",
        "building": "1",
        "floor": "1",
        "location": "测试",
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
    status, data = _post("/api/v1/formwork-check", incomplete)
    print(f"状态码: {status}")
    print(f"错误代码: {data['code']}")
    print(f"错误信息: {data['message']}")
    print(f"缺失参数: {data['missing_params']}")
    assert status == 400
    assert data['code'] == 'validation_error'
    assert 'missing_params' in data
    assert len(data['missing_params']) > 0
    for p in data['missing_params']:
        assert 'field' in p
        assert 'name' in p
        assert 'category' in p
        print(f"  [{p['category']}] {p['name']} ({p['field']})")
    print("✓ 通过\n")


def test_framework_validation_intercept():
    print("=" * 60)
    print("测试4：框架级字段缺失也被拦截（422→400）")
    print("=" * 60)

    very_incomplete = {
        "project_id": "PRJTEST",
        "building": "1"
    }
    status, data = _post("/api/v1/formwork-check", very_incomplete)
    print(f"状态码: {status}")
    print(f"错误代码: {data.get('code', 'N/A')}")
    print(f"错误信息: {data.get('message', 'N/A')}")
    if 'missing_params' in data:
        for p in data['missing_params']:
            print(f"  [{p['category']}] {p['name']} ({p['field']})")
    assert status == 400
    assert data.get('code') == 'validation_error'
    print("✓ 通过\n")


def test_batch_submit():
    print("=" * 60)
    print("测试5：批量提交验算任务")
    print("=" * 60)

    with open("examples/slab_example.json", "r", encoding="utf-8") as f:
        slab = json.load(f)
    with open("examples/beam_example.json", "r", encoding="utf-8") as f:
        beam = json.load(f)

    incomplete_task = {
        "project_id": "PRJBATCH",
        "project_name": "批量测试",
        "building": "1",
        "floor": "1",
        "location": "不完整任务",
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

    batch = {
        "tasks": [slab, beam, incomplete_task]
    }

    status, data = _post("/api/v1/formwork-check/batch", batch)
    print(f"状态码: {status}")
    print(f"总数: {data['total']}")
    print(f"成功: {data['success_count']}")
    print(f"失败: {data['fail_count']}")
    print(f"风险分布: {data['overall_risk_summary']}")

    for t in data['tasks']:
        if t['success']:
            print(f"  [{t['index']}] ✓ {t['task_code']} - {t['overall_risk_level']}")
        else:
            print(f"  [{t['index']}] ✗ 失败 - {t['error']['message']}")

    assert status == 200
    assert data['total'] == 3
    assert data['success_count'] == 2
    assert data['fail_count'] == 1
    print("✓ 通过\n")
    return [t['task_id'] for t in data['tasks'] if t['success']]


def test_enhanced_query():
    print("=" * 60)
    print("测试6：增强台账查询（多条件筛选）")
    print("=" * 60)

    status, data = _get("/api/v1/formwork-tasks?building=3&risk_level=medium&page_size=10")
    print(f"状态码: {status}")
    print(f"总数: {data['total']}")

    status2, data2 = _get(f"/api/v1/formwork-tasks?submitted_by={urllib.parse.quote('张工')}")
    print(f"按提交人筛选: {data2['total']}条")

    status3, data3 = _get(f"/api/v1/formwork-tasks?formwork_type={urllib.parse.quote('木模板')}")
    print(f"按模板类型筛选: {data3['total']}条")

    assert status == 200
    print("✓ 通过\n")


def test_csv_export():
    print("=" * 60)
    print("测试7：CSV导出")
    print("=" * 60)

    try:
        req = urllib.request.Request(f"{BASE_URL}/api/v1/formwork-tasks?export=csv")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8-sig')
            ct = resp.headers.get('Content-Type', '')
            cd = resp.headers.get('Content-Disposition', '')
            print(f"Content-Type: {ct}")
            print(f"Content-Disposition: {cd}")
            lines = content.strip().split('\n')
            print(f"行数: {len(lines)}")
            if lines:
                print(f"表头: {lines[0][:100]}")
            assert 'csv' in cd.lower() or 'attachment' in cd.lower()
            print("✓ 通过\n")
    except urllib.error.HTTPError as e:
        print(f"HTTP错误: {e.code}")
        print("✗ 失败\n")


def test_json_export():
    print("=" * 60)
    print("测试8：JSON导出")
    print("=" * 60)

    try:
        req = urllib.request.Request(f"{BASE_URL}/api/v1/formwork-tasks?export=json")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
            ct = resp.headers.get('Content-Type', '')
            cd = resp.headers.get('Content-Disposition', '')
            print(f"Content-Type: {ct}")
            print(f"Content-Disposition: {cd}")
            data = json.loads(content)
            print(f"导出条数: {len(data)}")
            assert isinstance(data, list)
            print("✓ 通过\n")
    except urllib.error.HTTPError as e:
        print(f"HTTP错误: {e.code}")
        print("✗ 失败\n")


def test_approval_voucher(task_id):
    print("=" * 60)
    print("测试9：审批流凭证")
    print("=" * 60)

    status, data = _get(f"/api/v1/formwork-voucher/{task_id}/approval")
    print(f"状态码: {status}")
    print(f"任务编号: {data['task_code']}")
    print(f"凭证编号: {data['voucher_code']}")

    print(f"\n输入参数摘要:")
    for item in data['input_summary']['items']:
        print(f"  {item['label']}: {item['value']}")

    print(f"\n关键分项验算:")
    for item in data['key_check_results']['items'][:3]:
        print(f"  {item['label']}: {item['ratio']} {'✓' if item['is_passed'] else '✗'}")

    print(f"\n总体结论:")
    for item in data['overall_conclusion']['items']:
        print(f"  {item['label']}: {item['value']}")

    print(f"\n不通过原因:")
    for item in data['failure_reasons']['items']:
        print(f"  {item['label']}: {item['value']}")

    assert status == 200
    assert 'input_summary' in data
    assert 'key_check_results' in data
    assert 'overall_conclusion' in data
    assert 'failure_reasons' in data
    print("✓ 通过\n")


def test_voucher_download(task_code):
    print("=" * 60)
    print("测试10：按任务编号下载凭证")
    print("=" * 60)

    try:
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/formwork-voucher/by-task-code/{task_code}/download"
        )
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
            ct = resp.headers.get('Content-Type', '')
            cd = resp.headers.get('Content-Disposition', '')
            print(f"Content-Type: {ct}")
            print(f"Content-Disposition: {cd}")
            data = json.loads(content)
            print(f"凭证编号: {data['voucher_code']}")
            print(f"项目: {data['project_name']}")
            print(f"部位: {data['location']}")
            print(f"风险等级: {data['overall_risk_level']}")
            print(f"结论文本长度: {len(data['conclusion'])}字")
            assert 'voucher_code' in data
            assert 'conclusion' in data
            assert 'input_params' in data
            print("✓ 通过\n")
    except urllib.error.HTTPError as e:
        print(f"HTTP错误: {e.code}")
        err = e.read().decode()
        print(f"响应: {err}")
        print("✗ 失败\n")


def main():
    print("\n" + "=" * 60)
    print("模板支撑验算服务 v2.0 - 全量测试")
    print("=" * 60 + "\n")

    try:
        test_health()
    except Exception as e:
        print(f"健康检查失败，服务未启动: {e}")
        return

    task_id, task_code = test_submit_single()
    test_unified_validation_error()
    test_framework_validation_intercept()
    batch_task_ids = test_batch_submit()
    test_enhanced_query()
    test_csv_export()
    test_json_export()
    test_approval_voucher(task_id)
    test_voucher_download(task_code)

    print("=" * 60)
    print("全量测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
