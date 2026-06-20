import io
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalculationTask, CheckResult, CalculationVoucher
from app.schemas import (
    FormworkCheckCreate,
    FormworkCheckResponse,
    BatchFormworkCheckCreate,
    BatchFormworkCheckResponse,
    BatchTaskResult,
    CheckResultItem,
    FormworkTaskListResponse,
    VoucherResponse,
    VoucherApprovalResponse,
    VoucherApprovalSection,
    MissingParam,
    ELEMENT_TYPE_MAP,
    RISK_LEVEL_MAP,
    PASS_STATUS_MAP,
    build_task_csv,
)
from app.validator import validate_formwork_params, group_missing_params
from app.calculator import run_formwork_check
from app.voucher_service import (
    generate_voucher_code,
    generate_conclusion,
    build_voucher_input,
    build_approval_voucher,
)
from app.exceptions import BusinessValidationError
from app.config import API_V1_PREFIX, RISK_LEVELS

router = APIRouter(prefix=API_V1_PREFIX, tags=["模板支撑验算"])


def generate_task_code(project_id: str) -> str:
    date_str = datetime.now().strftime('%Y%m%d')
    uid = uuid.uuid4().hex[:8].upper()
    return f"MB-{project_id[:8]}-{date_str}-{uid}"


def _process_single_task(data: FormworkCheckCreate, db: Session) -> dict:
    is_valid, missing_params = validate_formwork_params(data)

    if not is_valid:
        grouped = group_missing_params(missing_params)
        parts = [f"{cat}：{', '.join(fields)}" for cat, fields in grouped.items()]
        message = "缺少必要参数：" + "；".join(parts)
        return {
            "success": False,
            "error": {
                "code": "validation_error",
                "message": message,
                "missing_params": [p if isinstance(p, dict) else p.model_dump() for p in missing_params],
            }
        }

    task_code = generate_task_code(data.project_id)

    task = CalculationTask(
        task_code=task_code,
        project_id=data.project_id,
        project_name=data.project_name,
        building=data.building,
        floor=data.floor,
        location=data.location,
        element_type=data.element_type,
        formwork_type=data.formwork_type,
        support_height=data.support_height,
        element_length=data.element_length,
        element_width=data.element_width,
        element_height=data.element_height,
        slab_thickness=data.slab_thickness,
        panel_material=data.panel_material,
        panel_thickness=data.panel_thickness,
        secondary_beam_material=data.secondary_beam_material,
        secondary_beam_size=data.secondary_beam_size,
        secondary_beam_spacing=data.secondary_beam_spacing,
        main_beam_material=data.main_beam_material,
        main_beam_size=data.main_beam_size,
        main_beam_spacing=data.main_beam_spacing,
        pole_type=data.pole_type,
        pole_spacing_transverse=data.pole_spacing_transverse,
        pole_spacing_longitudinal=data.pole_spacing_longitudinal,
        horizontal_step=data.horizontal_step,
        construction_load=data.construction_load,
        status="calculating",
        submitted_by=data.submitted_by,
        remark=data.remark
    )
    db.add(task)
    db.flush()

    try:
        calc_result = run_formwork_check(data)
        overall = calc_result['overall']
        results = calc_result['results']

        task.status = "completed"
        task.overall_risk_level = overall['overall_risk_level']
        task.pass_status = overall['pass_status']
        task.failure_reasons = overall['failure_reasons']
        task.completed_at = datetime.utcnow()

        for r in results:
            result_item = CheckResult(
                task_id=task.id,
                check_item=r['check_item'],
                check_item_name=r['check_item_name'],
                calculated_value=r['calculated_value'],
                allowable_value=r['allowable_value'],
                ratio=r['ratio'],
                is_passed=1 if r['is_passed'] else 0,
                risk_level=r['risk_level'],
                detail=r.get('detail')
            )
            db.add(result_item)

        voucher_code = generate_voucher_code(data.project_id)
        conclusion = generate_conclusion(data, results, overall)
        input_params = build_voucher_input(data)

        approval_data = build_approval_voucher(data, results, overall)

        voucher = CalculationVoucher(
            task_id=task.id,
            voucher_code=voucher_code,
            input_params=input_params,
            calculation_process=calc_result['calculation_steps'],
            conclusion=conclusion
        )
        db.add(voucher)

        db.flush()

        result_items = []
        for r in results:
            result_items.append(CheckResultItem(
                check_item=r['check_item'],
                check_item_name=r['check_item_name'],
                calculated_value=r['calculated_value'],
                allowable_value=r['allowable_value'],
                ratio=r['ratio'],
                is_passed=r['is_passed'],
                risk_level=r['risk_level'],
                detail=r.get('detail')
            ))

        return {
            "success": True,
            "task_id": task.id,
            "task_code": task.task_code,
            "overall_risk_level": overall['overall_risk_level'],
            "pass_status": overall['pass_status'],
            "failure_reasons": overall['failure_reasons'],
            "results": result_items,
        }
    except Exception as e:
        task.status = "failed"
        db.flush()
        return {
            "success": False,
            "task_code": task_code,
            "error": {
                "code": "calculation_error",
                "message": f"验算计算异常：{str(e)}",
            }
        }


@router.post("/formwork-check", response_model=FormworkCheckResponse, summary="提交模板支撑验算任务")
def submit_formwork_check(data: FormworkCheckCreate, db: Session = Depends(get_db)):
    """
    提交模板支撑验算任务，进行参数完整性校验和力学验算。

    - **若参数不完整**：返回400错误，明确指出缺少哪类参数
    - **若参数完整**：执行12项验算，返回分项结果、总体风险等级和不通过原因
    """
    result = _process_single_task(data, db)

    if not result['success']:
        err = result['error']
        raise BusinessValidationError(
            code=err.get('code', 'validation_error'),
            message=err.get('message', '参数校验失败'),
            missing_params=err.get('missing_params'),
        )

    db.commit()

    task = db.query(CalculationTask).filter(CalculationTask.id == result['task_id']).first()
    return FormworkCheckResponse(
        task_id=result['task_id'],
        task_code=result['task_code'],
        status=task.status,
        overall_risk_level=result['overall_risk_level'],
        pass_status=result['pass_status'],
        failure_reasons=result['failure_reasons'],
        results=result['results'],
        submitted_at=task.submitted_at,
        completed_at=task.completed_at
    )


@router.post("/formwork-check/batch", response_model=BatchFormworkCheckResponse, summary="批量提交验算任务")
def batch_submit_formwork_check(data: BatchFormworkCheckCreate, db: Session = Depends(get_db)):
    """
    批量提交模板支撑验算任务。单条数据出错不影响其他任务入库。

    - 每条任务独立校验和计算
    - 返回每条任务的验算结果、失败原因
    - 汇总所有任务的风险等级分布
    - 最多一次提交200条
    """
    batch_results = []
    risk_summary = {"safe": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
    success_count = 0
    fail_count = 0

    for i, task_data in enumerate(data.tasks):
        result = _process_single_task(task_data, db)

        if result['success']:
            success_count += 1
            risk_summary[result['overall_risk_level']] = risk_summary.get(result['overall_risk_level'], 0) + 1
            batch_results.append(BatchTaskResult(
                index=i,
                success=True,
                task_code=result['task_code'],
                task_id=result['task_id'],
                overall_risk_level=result['overall_risk_level'],
                pass_status=result['pass_status'],
                failure_reasons=result['failure_reasons'],
                results=result['results'],
            ))
        else:
            fail_count += 1
            batch_results.append(BatchTaskResult(
                index=i,
                success=False,
                task_code=result.get('task_code'),
                error=result['error'],
                failure_reasons=result.get('failure_reasons'),
            ))

    db.commit()

    return BatchFormworkCheckResponse(
        total=len(data.tasks),
        success_count=success_count,
        fail_count=fail_count,
        overall_risk_summary=risk_summary,
        tasks=batch_results,
    )


@router.get("/formwork-check/{task_id}", response_model=FormworkCheckResponse, summary="查询验算任务详情")
def get_formwork_check(task_id: int, db: Session = Depends(get_db)):
    task = db.query(CalculationTask).filter(CalculationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "任务不存在"})

    results = db.query(CheckResult).filter(CheckResult.task_id == task_id).all()
    result_items = [_check_result_to_item(r) for r in results]

    return FormworkCheckResponse(
        task_id=task.id,
        task_code=task.task_code,
        status=task.status,
        overall_risk_level=task.overall_risk_level,
        pass_status=task.pass_status,
        failure_reasons=task.failure_reasons,
        results=result_items,
        submitted_at=task.submitted_at,
        completed_at=task.completed_at
    )


@router.get("/formwork-check/by-code/{task_code}", response_model=FormworkCheckResponse, summary="根据任务编号查询")
def get_formwork_check_by_code(task_code: str, db: Session = Depends(get_db)):
    task = db.query(CalculationTask).filter(CalculationTask.task_code == task_code).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "任务不存在"})

    results = db.query(CheckResult).filter(CheckResult.task_id == task.id).all()
    result_items = [_check_result_to_item(r) for r in results]

    return FormworkCheckResponse(
        task_id=task.id,
        task_code=task.task_code,
        status=task.status,
        overall_risk_level=task.overall_risk_level,
        pass_status=task.pass_status,
        failure_reasons=task.failure_reasons,
        results=result_items,
        submitted_at=task.submitted_at,
        completed_at=task.completed_at
    )


@router.get("/formwork-tasks", summary="查询验算历史台账")
def list_formwork_tasks(
    project_id: Optional[str] = Query(None, description="项目ID"),
    project_name: Optional[str] = Query(None, description="项目名称（模糊匹配）"),
    building: Optional[str] = Query(None, description="楼栋号"),
    floor: Optional[str] = Query(None, description="楼层"),
    formwork_type: Optional[str] = Query(None, description="模板类型"),
    risk_level: Optional[str] = Query(None, description="风险等级：safe/low/medium/high/critical"),
    pass_status: Optional[str] = Query(None, description="通过状态：pass/warning/fail"),
    submitted_by: Optional[str] = Query(None, description="提交人"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    export: Optional[str] = Query(None, description="导出格式：csv 或 json，不传则分页返回"),
    db: Session = Depends(get_db)
):
    """
    验算历史台账查询，支持多条件组合筛选。

    - 可按项目、楼栋、楼层、模板类型、风险等级、提交人、日期范围组合筛选
    - 传入 export=csv 或 export=json 可导出全量数据（忽略分页）
    - 不传 export 参数则分页返回
    """
    query = db.query(CalculationTask)

    if project_id:
        query = query.filter(CalculationTask.project_id == project_id)
    if project_name:
        query = query.filter(CalculationTask.project_name.contains(project_name))
    if building:
        query = query.filter(CalculationTask.building == building)
    if floor:
        query = query.filter(CalculationTask.floor == floor)
    if formwork_type:
        query = query.filter(CalculationTask.formwork_type == formwork_type)
    if risk_level:
        query = query.filter(CalculationTask.overall_risk_level == risk_level)
    if pass_status:
        query = query.filter(CalculationTask.pass_status == pass_status)
    if submitted_by:
        query = query.filter(CalculationTask.submitted_by == submitted_by)
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(CalculationTask.submitted_at >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(CalculationTask.submitted_at <= end_dt)

    query = query.order_by(CalculationTask.submitted_at.desc())

    if export == 'json':
        tasks = query.all()
        items = [_task_to_dict(t) for t in tasks]
        return StreamingResponse(
            io.BytesIO(_json_bytes(items)),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=formwork_tasks.json"}
        )

    if export == 'csv':
        tasks = query.all()
        items = [_task_to_dict(t) for t in tasks]
        csv_content = build_task_csv(items)
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=formwork_tasks.csv"}
        )

    total = query.count()
    paged_query = query.offset((page - 1) * page_size).limit(page_size)
    tasks = paged_query.all()
    items = [_task_to_dict(t) for t in tasks]

    return FormworkTaskListResponse(total=total, items=items)


@router.get("/formwork-voucher/{task_id}", response_model=VoucherResponse, summary="获取计算凭证（完整）")
def get_calculation_voucher(task_id: int, db: Session = Depends(get_db)):
    voucher = db.query(CalculationVoucher).filter(CalculationVoucher.task_id == task_id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "计算凭证不存在"})

    return VoucherResponse(
        task_id=voucher.task_id,
        voucher_code=voucher.voucher_code,
        input_params=voucher.input_params,
        calculation_process=voucher.calculation_process,
        conclusion=voucher.conclusion,
        created_at=voucher.created_at
    )


@router.get("/formwork-voucher/by-code/{voucher_code}", response_model=VoucherResponse, summary="根据凭证号查询")
def get_voucher_by_code(voucher_code: str, db: Session = Depends(get_db)):
    voucher = db.query(CalculationVoucher).filter(CalculationVoucher.voucher_code == voucher_code).first()
    if not voucher:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "计算凭证不存在"})

    return VoucherResponse(
        task_id=voucher.task_id,
        voucher_code=voucher.voucher_code,
        input_params=voucher.input_params,
        calculation_process=voucher.calculation_process,
        conclusion=voucher.conclusion,
        created_at=voucher.created_at
    )


@router.get("/formwork-voucher/{task_id}/approval", response_model=VoucherApprovalResponse, summary="获取审批流凭证")
def get_approval_voucher(task_id: int, db: Session = Depends(get_db)):
    """
    获取适合审批流展示的结构化凭证，包含输入参数摘要、关键分项验算、总体结论和不通过原因。
    """
    task = db.query(CalculationTask).filter(CalculationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "任务不存在"})

    voucher = db.query(CalculationVoucher).filter(CalculationVoucher.task_id == task_id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "计算凭证不存在"})

    results = db.query(CheckResult).filter(CheckResult.task_id == task_id).all()
    result_dicts = []
    for r in results:
        result_dicts.append({
            "check_item": r.check_item,
            "check_item_name": r.check_item_name,
            "calculated_value": r.calculated_value,
            "allowable_value": r.allowable_value,
            "ratio": r.ratio,
            "is_passed": bool(r.is_passed),
            "risk_level": r.risk_level,
        })

    input_summary_items = [
        {"label": "项目名称", "value": task.project_name},
        {"label": "楼栋/楼层", "value": f"{task.building}号楼 {task.floor}层"},
        {"label": "工程部位", "value": task.location},
        {"label": "构件类型", "value": ELEMENT_TYPE_MAP.get(task.element_type, task.element_type)},
        {"label": "模板类型", "value": task.formwork_type},
        {"label": "支架高度", "value": f"{task.support_height}m"},
        {"label": "面板", "value": f"{task.panel_material} {task.panel_thickness}mm"},
        {"label": "次楞", "value": f"{task.secondary_beam_material} {task.secondary_beam_size} @{task.secondary_beam_spacing}mm"},
        {"label": "主楞", "value": f"{task.main_beam_material} {task.main_beam_size} @{task.main_beam_spacing}mm"},
        {"label": "立杆", "value": f"{task.pole_type} {task.pole_spacing_transverse}×{task.pole_spacing_longitudinal}mm 步距{task.horizontal_step}mm"},
    ]

    if task.slab_thickness:
        input_summary_items.append({"label": "板厚", "value": f"{task.slab_thickness}mm"})

    key_check_items = []
    for r in results:
        key_check_items.append({
            "label": r.check_item_name,
            "calculated_value": r.calculated_value,
            "allowable_value": r.allowable_value,
            "ratio": round(r.ratio, 3),
            "is_passed": bool(r.is_passed),
            "risk_level": RISK_LEVEL_MAP.get(r.risk_level, r.risk_level),
        })

    risk_cn = RISK_LEVEL_MAP.get(task.overall_risk_level, task.overall_risk_level or "")
    pass_cn = PASS_STATUS_MAP.get(task.pass_status, task.pass_status or "")

    overall_items = [
        {"label": "风险等级", "value": risk_cn},
        {"label": "通过状态", "value": pass_cn},
        {"label": "验算时间", "value": task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else ""},
        {"label": "提交人", "value": task.submitted_by or ""},
    ]

    failure_items = []
    if task.failure_reasons:
        for i, reason in enumerate(task.failure_reasons, 1):
            failure_items.append({"label": f"原因{i}", "value": reason})
    else:
        failure_items.append({"label": "说明", "value": "无"})

    return VoucherApprovalResponse(
        task_id=task.id,
        task_code=task.task_code,
        voucher_code=voucher.voucher_code,
        created_at=voucher.created_at,
        input_summary=VoucherApprovalSection(title="输入参数摘要", items=input_summary_items),
        key_check_results=VoucherApprovalSection(title="关键分项验算", items=key_check_items),
        overall_conclusion=VoucherApprovalSection(title="总体结论", items=overall_items),
        failure_reasons=VoucherApprovalSection(title="不通过原因", items=failure_items),
    )


@router.get("/formwork-voucher/by-task-code/{task_code}/download", summary="按任务编号下载凭证")
def download_voucher_by_task_code(task_code: str, db: Session = Depends(get_db)):
    """
    根据任务编号直接下载凭证内容（JSON格式）。
    """
    task = db.query(CalculationTask).filter(CalculationTask.task_code == task_code).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "任务不存在"})

    voucher = db.query(CalculationVoucher).filter(CalculationVoucher.task_id == task.id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "计算凭证不存在"})

    content = {
        "task_id": task.id,
        "task_code": task.task_code,
        "voucher_code": voucher.voucher_code,
        "project_name": task.project_name,
        "building": task.building,
        "floor": task.floor,
        "location": task.location,
        "element_type": task.element_type,
        "overall_risk_level": task.overall_risk_level,
        "pass_status": task.pass_status,
        "failure_reasons": task.failure_reasons,
        "input_params": voucher.input_params,
        "calculation_process": voucher.calculation_process,
        "conclusion": voucher.conclusion,
        "submitted_at": task.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if task.submitted_at else None,
        "completed_at": task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else None,
        "voucher_created_at": voucher.created_at.strftime("%Y-%m-%d %H:%M:%S") if voucher.created_at else None,
    }

    import json
    json_bytes = json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')
    filename = f"voucher_{task_code}.json"

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _check_result_to_item(r: CheckResult) -> CheckResultItem:
    return CheckResultItem(
        check_item=r.check_item,
        check_item_name=r.check_item_name,
        calculated_value=r.calculated_value,
        allowable_value=r.allowable_value,
        ratio=r.ratio,
        is_passed=bool(r.is_passed),
        risk_level=r.risk_level,
        detail=r.detail
    )


def _task_to_dict(task: CalculationTask) -> dict:
    return {
        'task_id': task.id,
        'task_code': task.task_code,
        'project_id': task.project_id,
        'project_name': task.project_name,
        'building': task.building,
        'floor': task.floor,
        'location': task.location,
        'element_type': task.element_type,
        'formwork_type': task.formwork_type,
        'support_height': task.support_height,
        'overall_risk_level': task.overall_risk_level,
        'pass_status': task.pass_status,
        'submitted_by': task.submitted_by,
        'submitted_at': task.submitted_at,
        'completed_at': task.completed_at
    }


def _json_bytes(items: list) -> bytes:
    import json
    def _default(o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(items, ensure_ascii=False, indent=2, default=_default).encode('utf-8')
