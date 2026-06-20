"""
模板支撑验算服务 - 边缘场景测试

覆盖场景：
1. 空库启动 → 健康检查 → 单条提交 → 查询详情 → 查台账 → 拿凭证
2. 批量提交混入缺字段任务（面板材料、主楞规格、立杆间距）
3. 批量提交后查台账，成功任务正常入库，失败任务不入库
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8080"


def _get(path):
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return resp.status, json.loads(resp.read())


def _post(path, body):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


SLAB_TASK = {
    "project_id": "PRJ2024001",
    "project_name": "阳光花园住宅小区",
    "building": "3",
    "floor": "5",
    "location": "3号楼5层顶板东侧",
    "element_type": "slab",
    "formwork_type": "木模板",
    "support_height": 3.2,
    "slab_thickness": 120,
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
    "horizontal_step": 1500,
    "construction_load": 2.0,
    "submitted_by": "王工",
    "remark": "标准层楼板"
}

BEAM_TASK = {
    "project_id": "PRJ2024001",
    "project_name": "阳光花园住宅小区",
    "building": "3",
    "floor": "5",
    "location": "3号楼5层梁L-01",
    "element_type": "beam",
    "formwork_type": "木模板",
    "support_height": 3.2,
    "element_width": 300,
    "element_height": 600,
    "panel_material": "plywood_15",
    "panel_thickness": 15,
    "secondary_beam_material": "wood_pine",
    "secondary_beam_size": "50x100",
    "secondary_beam_spacing": 300,
    "main_beam_material": "wood_pine",
    "main_beam_size": "50x100",
    "main_beam_spacing": 1000,
    "pole_type": "steel_48x35",
    "pole_spacing_transverse": 900,
    "pole_spacing_longitudinal": 1000,
    "horizontal_step": 1500,
    "construction_load": 2.0,
    "submitted_by": "王工",
    "remark": "主梁"
}


def test1_empty_db_startup():
    """测试1：空库启动全流程"""
    print("=" * 60)
    print("测试1：空库启动 → 提交 → 查询 → 台账 → 凭证")
    print("=" * 60)

    # 健康检查
    status, data = _get("/health")
    assert status == 200, f"健康检查失败: {status}"
    assert data["status"] == "ok"
    print(f"  ✓ 健康检查: {data['service']} v{data['version']}")

    # 单条提交楼板
    status, data = _post("/api/v1/formwork-check", SLAB_TASK)
    assert status == 200, f"提交失败: {status} {data}"
    assert data["pass_status"] in ("pass", "warning", "fail")
    task_id = data["task_id"]
    task_code = data["task_code"]
    print(f"  ✓ 单条提交成功: task_id={task_id}, risk={data['overall_risk_level']}")

    # 查询详情
    status, data = _get(f"/api/v1/formwork-check/{task_id}")
    assert status == 200
    assert data["task_code"] == task_code
    assert len(data["results"]) == 12
    print(f"  ✓ 任务详情查询: {len(data['results'])}项验算结果")

    # 按编号查询
    status, data = _get(f"/api/v1/formwork-check/by-code/{task_code}")
    assert status == 200
    assert data["task_id"] == task_id
    print(f"  ✓ 按编号查询: 匹配成功")

    # 台账查询
    status, data = _get("/api/v1/formwork-tasks?submitted_by=" + urllib.parse.quote("王工"))
    assert status == 200
    assert data["total"] >= 1
    print(f"  ✓ 台账查询: 共{data['total']}条")

    # 审批流凭证
    status, data = _get(f"/api/v1/formwork-voucher/{task_id}/approval")
    assert status == 200
    assert data["input_summary"]["title"] == "输入参数摘要"
    assert data["overall_conclusion"]["title"] == "总体结论"
    print(f"  ✓ 审批流凭证: 4个板块完整")

    # 凭证下载
    req = urllib.request.Request(f"{BASE_URL}/api/v1/formwork-voucher/by-task-code/{task_code}/download")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content = json.loads(resp.read())
        assert content["task_code"] == task_code
        assert "conclusion" in content
        print(f"  ✓ 凭证下载: conclusion长度={len(content['conclusion'])}字")

    print("✓ 测试1通过\n")
    return task_id, task_code


def test2_batch_with_missing_fields():
    """测试2：批量提交混入缺字段任务"""
    print("=" * 60)
    print("测试2：批量提交混入缺字段任务（Pydantic级缺失）")
    print("=" * 60)

    # 任务1：完整楼板
    task1 = dict(SLAB_TASK)
    task1["location"] = "批量-楼板-完整"
    task1["submitted_by"] = "批量测试员"

    # 任务2：缺面板材料 (Pydantic required 字段)
    task2 = dict(SLAB_TASK)
    task2["location"] = "批量-楼板-缺面板材料"
    task2["submitted_by"] = "批量测试员"
    del task2["panel_material"]

    # 任务3：完整梁
    task3 = dict(BEAM_TASK)
    task3["location"] = "批量-梁-完整"
    task3["submitted_by"] = "批量测试员"

    # 任务4：缺主楞规格 (Pydantic required 字段)
    task4 = dict(BEAM_TASK)
    task4["location"] = "批量-梁-缺主楞规格"
    task4["submitted_by"] = "批量测试员"
    del task4["main_beam_size"]

    # 任务5：缺立杆纵距 (Pydantic required 字段)
    task5 = dict(SLAB_TASK)
    task5["location"] = "批量-楼板-缺立杆纵距"
    task5["submitted_by"] = "批量测试员"
    del task5["pole_spacing_longitudinal"]

    batch_body = {"tasks": [task1, task2, task3, task4, task5]}
    status, data = _post("/api/v1/formwork-check/batch", batch_body)

    assert status == 200, f"批量提交返回状态错误: {status} {data}"
    assert data["total"] == 5
    assert data["success_count"] == 2, f"成功数应为2，实际{data['success_count']}"
    assert data["fail_count"] == 3, f"失败数应为3，实际{data['fail_count']}"
    print(f"  ✓ 整批返回成功: 总数={data['total']}, 成功={data['success_count']}, 失败={data['fail_count']}")

    # 验证风险汇总与成功数一致
    risk_total = sum(data["overall_risk_summary"].values())
    assert risk_total == data["success_count"], f"风险汇总总数{risk_total} ≠ 成功数{data['success_count']}"
    print(f"  ✓ 风险汇总与成功数一致: {risk_total}项")

    # 逐条验证
    results = data["tasks"]

    # 第0条：完整楼板 → 应成功
    assert results[0]["success"] is True
    assert results[0]["task_code"] is not None
    assert "overall_risk_level" in results[0]
    print(f"  [0] ✓ 完整楼板: {results[0]['task_code']} - {results[0]['overall_risk_level']}")

    # 第1条：缺面板材料 → 应失败
    assert results[1]["success"] is False
    err = results[1]["error"]
    assert err["code"] == "validation_error"
    assert "missing_params" in err
    fields_missing = [p["field"] for p in err["missing_params"]]
    assert "panel_material" in fields_missing, f"应报告缺panel_material，实际缺: {fields_missing}"
    # 检查分类
    categories = {p["category"] for p in err["missing_params"]}
    assert "材料参数" in categories, f"应包含材料参数分类，实际: {categories}"
    print(f"  [1] ✗ 缺面板材料: {err['message'][:50]}...")
    print(f"      缺字段: {fields_missing}")
    print(f"      分类: {list(categories)}")

    # 第2条：完整梁 → 应成功
    assert results[2]["success"] is True
    print(f"  [2] ✓ 完整梁: {results[2]['task_code']} - {results[2]['overall_risk_level']}")

    # 第3条：缺主楞规格 → 应失败
    assert results[3]["success"] is False
    err3 = results[3]["error"]
    fields3 = [p["field"] for p in err3["missing_params"]]
    assert "main_beam_size" in fields3
    cats3 = {p["category"] for p in err3["missing_params"]}
    assert "楞梁参数" in cats3
    print(f"  [3] ✗ 缺主楞规格: {[p['name'] for p in err3['missing_params'] if p['field']=='main_beam_size']}")

    # 第4条：缺立杆纵距 → 应失败
    assert results[4]["success"] is False
    err4 = results[4]["error"]
    fields4 = [p["field"] for p in err4["missing_params"]]
    assert "pole_spacing_longitudinal" in fields4
    cats4 = {p["category"] for p in err4["missing_params"]}
    assert "支架参数" in cats4
    print(f"  [4] ✗ 缺立杆纵距: {[p['name'] for p in err4['missing_params'] if p['field']=='pole_spacing_longitudinal']}")

    print("✓ 测试2通过\n")
    return data


def test3_batch_then_query_ledger():
    """测试3：批量提交后查台账，成功任务入库，失败任务不入库"""
    print("=" * 60)
    print("测试3：批量后台账查询验证")
    print("=" * 60)

    # 查询"批量测试员"提交的任务
    status, data = _get("/api/v1/formwork-tasks?submitted_by=" + urllib.parse.quote("批量测试员"))
    assert status == 200

    # 批量提交了2条成功的（楼板+梁），之前测试1有1条王工的，这里只数批量测试员的
    assert data["total"] == 2, f"应只有2条成功任务入库，实际{data['total']}条"
    print(f"  ✓ 台账查询: 批量测试员提交的任务共{data['total']}条（成功的都入库了）")

    locations = [item["location"] for item in data["items"]]
    assert "批量-楼板-完整" in locations
    assert "批量-梁-完整" in locations
    assert "批量-楼板-缺面板材料" not in locations
    assert "批量-梁-缺主楞规格" not in locations
    assert "批量-楼板-缺立杆纵距" not in locations
    print(f"  ✓ 成功任务在台账中，失败任务不在")

    # 验证每条成功任务都能拿到凭证
    for item in data["items"]:
        tid = item["task_id"]
        status, voucher = _get(f"/api/v1/formwork-voucher/{tid}/approval")
        assert status == 200
        assert voucher["overall_conclusion"]["items"]
    print(f"  ✓ 所有成功任务都有审批流凭证")

    print("✓ 测试3通过\n")


def test4_single_validation_error_format():
    """测试4：单条提交缺字段的错误格式与批量一致"""
    print("=" * 60)
    print("测试4：单条缺字段错误格式一致性")
    print("=" * 60)

    # 单条：缺面板材料
    bad_task = dict(SLAB_TASK)
    del bad_task["panel_material"]
    status, data = _post("/api/v1/formwork-check", bad_task)

    assert status == 400
    assert data["code"] == "validation_error"
    assert "missing_params" in data

    fields = [p["field"] for p in data["missing_params"]]
    assert "panel_material" in fields

    categories = {p["category"] for p in data["missing_params"]}
    assert "材料参数" in categories

    print(f"  ✓ 单条400错误格式统一")
    print(f"  ✓ 缺字段: {fields}")
    print(f"  ✓ 分类: {list(categories)}")
    print(f"  ✓ message: {data['message'][:60]}...")

    # 对比批量中的错误格式
    batch_body = {"tasks": [bad_task]}
    status2, data2 = _post("/api/v1/formwork-check/batch", batch_body)
    assert status2 == 200
    batch_err = data2["tasks"][0]["error"]

    # 错误结构应该一致：有 code/message/missing_params
    assert batch_err["code"] == data["code"]
    batch_fields = [p["field"] for p in batch_err["missing_params"]]
    assert batch_fields == fields
    print(f"  ✓ 批量内单条错误格式与单条接口一致")

    print("✓ 测试4通过\n")


def main():
    print("\n" + "=" * 60)
    print("模板支撑验算服务 v2.1 - 边缘场景测试")
    print("=" * 60 + "\n")

    try:
        test1_empty_db_startup()
        test2_batch_with_missing_fields()
        test3_batch_then_query_ledger()
        test4_single_validation_error_format()

        print("=" * 60)
        print("全部边缘场景测试通过 ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ 断言失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
