import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalculationTask, CheckResult, CalculationVoucher
from app.schemas import (
    FormworkCheckCreate,
    FormworkCheckResponse,
    CheckResultItem,
    FormworkTaskListResponse,
    ValidationErrorResponse,
    VoucherResponse
)
from app.validator import validate_formwork_params, group_missing_params
from app.calculator import run_formwork_check
from app.voucher_service import generate_voucher_code, generate_conclusion, build_voucher_input
from app.config import API_V1_PREFIX

router = APIRouter(prefix=API_V1_PREFIX, tags=["模板支撑验算"])


def generate_task_code(project_id: str) -> str:
    date_str = datetime.now().strftime('%Y%m%d')
    uid = uuid.uuid4().hex[:8].upper()
    return f"MB-{project_id[:8]}-{date_str}-{uid}"


@router.post("/formwork-check", response_model=FormworkCheckResponse, summary="提交模板支撑验算任务")
def submit_formwork_check(data: FormworkCheckCreate, db: Session = Depends(get_db)):
    """
    提交模板支撑验算任务，进行参数完整性校验和力学验算。

    - **若参数不完整**：返回400错误，明确指出缺少哪类参数
    - **若参数完整**：执行12项验算，返回分项结果、总体风险等级和不通过原因
    """
    is_valid, missing_params = validate_formwork_params(data)

    if not is_valid:
        grouped = group_missing_params(missing_params)
        error_msg_parts = []
        for category, fields in grouped.items():
            error_msg_parts.append(f"{category}：{', '.join(fields)}")
        error_msg = "缺少必要参数：" + "；".join(error_msg_parts)

        raise HTTPException(
            status_code=400,
            detail={
                "code": "validation_error",
                "message": error_msg,
                "missing_params": missing_params
            }
        )

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

    voucher = CalculationVoucher(
        task_id=task.id,
        voucher_code=voucher_code,
        input_params=input_params,
        calculation_process=calc_result['calculation_steps'],
        conclusion=conclusion
    )
    db.add(voucher)

    db.commit()
    db.refresh(task)

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


@router.get("/formwork-check/{task_id}", response_model=FormworkCheckResponse, summary="查询验算任务详情")
def get_formwork_check(task_id: int, db: Session = Depends(get_db)):
    """
    根据任务ID查询验算任务详情，包含分项验算结果
    """
    task = db.query(CalculationTask).filter(CalculationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    results = db.query(CheckResult).filter(CheckResult.task_id == task_id).all()
    result_items = []
    for r in results:
        result_items.append(CheckResultItem(
            check_item=r.check_item,
            check_item_name=r.check_item_name,
            calculated_value=r.calculated_value,
            allowable_value=r.allowable_value,
            ratio=r.ratio,
            is_passed=bool(r.is_passed),
            risk_level=r.risk_level,
            detail=r.detail
        ))

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
    """
    根据任务编号查询验算任务详情
    """
    task = db.query(CalculationTask).filter(CalculationTask.task_code == task_code).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    results = db.query(CheckResult).filter(CheckResult.task_id == task.id).all()
    result_items = []
    for r in results:
        result_items.append(CheckResultItem(
            check_item=r.check_item,
            check_item_name=r.check_item_name,
            calculated_value=r.calculated_value,
            allowable_value=r.allowable_value,
            ratio=r.ratio,
            is_passed=bool(r.is_passed),
            risk_level=r.risk_level,
            detail=r.detail
        ))

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


@router.get("/formwork-tasks", response_model=FormworkTaskListResponse, summary="查询验算历史记录")
def list_formwork_tasks(
    project_id: Optional[str] = Query(None, description="项目ID"),
    building: Optional[str] = Query(None, description="楼栋号"),
    floor: Optional[str] = Query(None, description="楼层"),
    risk_level: Optional[str] = Query(None, description="风险等级"),
    pass_status: Optional[str] = Query(None, description="通过状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    按项目、楼栋、楼层、日期等条件查询历史验算记录
    """
    query = db.query(CalculationTask)

    if project_id:
        query = query.filter(CalculationTask.project_id == project_id)
    if building:
        query = query.filter(CalculationTask.building == building)
    if floor:
        query = query.filter(CalculationTask.floor == floor)
    if risk_level:
        query = query.filter(CalculationTask.overall_risk_level == risk_level)
    if pass_status:
        query = query.filter(CalculationTask.pass_status == pass_status)
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(CalculationTask.submitted_at >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(CalculationTask.submitted_at <= end_dt)

    total = query.count()

    query = query.order_by(CalculationTask.submitted_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    tasks = query.all()

    items = []
    for task in tasks:
        items.append({
            'task_id': task.id,
            'task_code': task.task_code,
            'project_id': task.project_id,
            'project_name': task.project_name,
            'building': task.building,
            'floor': task.floor,
            'location': task.location,
            'element_type': task.element_type,
            'support_height': task.support_height,
            'overall_risk_level': task.overall_risk_level,
            'pass_status': task.pass_status,
            'submitted_by': task.submitted_by,
            'submitted_at': task.submitted_at,
            'completed_at': task.completed_at
        })

    return FormworkTaskListResponse(total=total, items=items)


@router.get("/formwork-voucher/{task_id}", response_model=VoucherResponse, summary="获取计算凭证")
def get_calculation_voucher(task_id: int, db: Session = Depends(get_db)):
    """
    获取验算任务的计算凭证，包含完整的输入参数、计算过程和结论
    """
    voucher = db.query(CalculationVoucher).filter(CalculationVoucher.task_id == task_id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="计算凭证不存在")

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
    """
    根据凭证编号查询计算凭证
    """
    voucher = db.query(CalculationVoucher).filter(CalculationVoucher.voucher_code == voucher_code).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="计算凭证不存在")

    return VoucherResponse(
        task_id=voucher.task_id,
        voucher_code=voucher.voucher_code,
        input_params=voucher.input_params,
        calculation_process=voucher.calculation_process,
        conclusion=voucher.conclusion,
        created_at=voucher.created_at
    )
