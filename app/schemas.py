import csv
import io
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class FormworkCheckCreate(BaseModel):
    project_id: str = Field(..., max_length=64, description="项目ID")
    project_name: str = Field(..., max_length=256, description="项目名称")
    building: str = Field(..., max_length=64, description="楼栋号")
    floor: str = Field(..., max_length=64, description="楼层")
    location: str = Field(..., max_length=256, description="工程部位")
    element_type: str = Field(..., max_length=32, description="构件类型：slab-楼板, beam-梁, column-柱, wall-墙")
    formwork_type: str = Field(..., max_length=32, description="模板类型")
    support_height: float = Field(..., gt=0, description="支架高度(m)")
    element_length: Optional[float] = Field(None, gt=0, description="构件长度(m)")
    element_width: Optional[float] = Field(None, gt=0, description="构件宽度(m)")
    element_height: Optional[float] = Field(None, gt=0, description="构件高度(m)")
    slab_thickness: Optional[float] = Field(None, gt=0, description="板厚(mm)")
    panel_material: str = Field(..., max_length=64, description="面板材料")
    panel_thickness: float = Field(..., gt=0, description="面板厚度(mm)")
    secondary_beam_material: str = Field(..., max_length=64, description="次楞材料")
    secondary_beam_size: str = Field(..., max_length=64, description="次楞规格")
    secondary_beam_spacing: float = Field(..., gt=0, description="次楞间距(mm)")
    main_beam_material: str = Field(..., max_length=64, description="主楞材料")
    main_beam_size: str = Field(..., max_length=64, description="主楞规格")
    main_beam_spacing: float = Field(..., gt=0, description="主楞间距(mm)")
    pole_type: str = Field(..., max_length=64, description="立杆类型")
    pole_spacing_transverse: float = Field(..., gt=0, description="立杆横距(mm)")
    pole_spacing_longitudinal: float = Field(..., gt=0, description="立杆纵距(mm)")
    horizontal_step: float = Field(..., gt=0, description="水平杆步距(mm)")
    construction_load: Optional[float] = Field(None, ge=0, description="施工荷载(kN/m²)")
    submitted_by: Optional[str] = Field(None, max_length=128, description="提交人")
    remark: Optional[str] = Field(None, description="备注")

    @field_validator('element_type')
    @classmethod
    def validate_element_type(cls, v):
        valid_types = ['slab', 'beam', 'column', 'wall']
        if v not in valid_types:
            raise ValueError(f'element_type must be one of {valid_types}')
        return v


class BatchFormworkCheckCreate(BaseModel):
    tasks: List[FormworkCheckCreate] = Field(..., min_length=1, max_length=200, description="验算任务列表，最多200条")


class CheckResultItem(BaseModel):
    check_item: str
    check_item_name: str
    calculated_value: float
    allowable_value: float
    ratio: float
    is_passed: bool
    risk_level: str
    detail: Optional[Dict[str, Any]] = None


class FormworkCheckResponse(BaseModel):
    task_id: int
    task_code: str
    status: str
    overall_risk_level: Optional[str] = None
    pass_status: Optional[str] = None
    failure_reasons: Optional[List[str]] = None
    results: Optional[List[CheckResultItem]] = None
    submitted_at: datetime
    completed_at: Optional[datetime] = None


class BatchTaskResult(BaseModel):
    index: int
    success: bool
    task_code: Optional[str] = None
    task_id: Optional[int] = None
    overall_risk_level: Optional[str] = None
    pass_status: Optional[str] = None
    failure_reasons: Optional[List[str]] = None
    results: Optional[List[CheckResultItem]] = None
    error: Optional[Dict[str, Any]] = None


class BatchFormworkCheckResponse(BaseModel):
    total: int
    success_count: int
    fail_count: int
    overall_risk_summary: Dict[str, int]
    tasks: List[BatchTaskResult]


class FormworkTaskListResponse(BaseModel):
    total: int
    items: List[Dict[str, Any]]


class MissingParam(BaseModel):
    field: str
    name: str
    category: str


class UnifiedErrorResponse(BaseModel):
    code: str
    message: str
    missing_params: Optional[List[MissingParam]] = None
    detail: Optional[Any] = None


class VoucherApprovalSection(BaseModel):
    title: str
    items: List[Dict[str, Any]]


class VoucherApprovalResponse(BaseModel):
    task_id: int
    task_code: str
    voucher_code: str
    created_at: datetime
    input_summary: VoucherApprovalSection
    key_check_results: VoucherApprovalSection
    overall_conclusion: VoucherApprovalSection
    failure_reasons: VoucherApprovalSection


class VoucherResponse(BaseModel):
    task_id: int
    voucher_code: str
    input_params: Dict[str, Any]
    calculation_process: Dict[str, Any]
    conclusion: str
    created_at: datetime


ELEMENT_TYPE_MAP = {
    "slab": "楼板",
    "beam": "梁",
    "column": "柱",
    "wall": "墙",
}

RISK_LEVEL_MAP = {
    "safe": "安全",
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "重大风险",
}

PASS_STATUS_MAP = {
    "pass": "通过",
    "warning": "警示",
    "fail": "不通过",
}


def _build_missing_params_from_validation_error(exc: RequestValidationError) -> List[MissingParam]:
    field_category_map = {
        "project_id": ("项目ID", "基础信息"),
        "project_name": ("项目名称", "基础信息"),
        "building": ("楼栋号", "基础信息"),
        "floor": ("楼层", "基础信息"),
        "location": ("工程部位", "基础信息"),
        "element_type": ("构件类型", "基础信息"),
        "formwork_type": ("模板类型", "基础信息"),
        "support_height": ("支架高度", "几何参数"),
        "element_length": ("构件长度", "几何参数"),
        "element_width": ("构件宽度", "几何参数"),
        "element_height": ("构件高度", "几何参数"),
        "slab_thickness": ("板厚", "几何参数"),
        "panel_material": ("面板材料", "材料参数"),
        "panel_thickness": ("面板厚度", "材料参数"),
        "secondary_beam_material": ("次楞材料", "楞梁参数"),
        "secondary_beam_size": ("次楞规格", "楞梁参数"),
        "secondary_beam_spacing": ("次楞间距", "楞梁参数"),
        "main_beam_material": ("主楞材料", "楞梁参数"),
        "main_beam_size": ("主楞规格", "楞梁参数"),
        "main_beam_spacing": ("主楞间距", "楞梁参数"),
        "pole_type": ("立杆类型", "支架参数"),
        "pole_spacing_transverse": ("立杆横距", "支架参数"),
        "pole_spacing_longitudinal": ("立杆纵距", "支架参数"),
        "horizontal_step": ("水平杆步距", "支架参数"),
        "construction_load": ("施工荷载", "荷载参数"),
    }

    missing = []
    seen = set()
    for err in exc.errors():
        if err["type"] == "missing":
            field_name = err["loc"][-1] if err["loc"] else "unknown"
        elif err["type"] == "value_error":
            field_name = err["loc"][-1] if err["loc"] else "unknown"
        elif err["type"] == "greater_than" or err["type"] == "greater_than_equal":
            field_name = err["loc"][-1] if err["loc"] else "unknown"
        else:
            field_name = err["loc"][-1] if err["loc"] else "unknown"

        if field_name in seen:
            continue
        seen.add(field_name)

        cn_name, category = field_category_map.get(field_name, (field_name, "其他"))
        missing.append(MissingParam(field=field_name, name=cn_name, category=category))

    return missing


async def unified_validation_exception_handler(request: Request, exc: RequestValidationError):
    missing_params = _build_missing_params_from_validation_error(exc)

    if missing_params:
        grouped = {}
        for p in missing_params:
            grouped.setdefault(p.category, []).append(p.name)

        parts = [f"{cat}：{', '.join(fields)}" for cat, fields in grouped.items()]
        message = "缺少必要参数：" + "；".join(parts)

        return JSONResponse(
            status_code=400,
            content={
                "code": "validation_error",
                "message": message,
                "missing_params": [p.model_dump() for p in missing_params],
            }
        )

    return JSONResponse(
        status_code=400,
        content={
            "code": "validation_error",
            "message": "请求数据格式错误",
            "detail": exc.errors(),
        }
    )


def build_task_csv(tasks: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    fieldnames = [
        "task_id", "task_code", "project_id", "project_name",
        "building", "floor", "location", "element_type", "formwork_type",
        "support_height", "overall_risk_level", "pass_status",
        "submitted_by", "submitted_at", "completed_at"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for task in tasks:
        row = {}
        for f in fieldnames:
            val = task.get(f, "")
            if isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d %H:%M:%S")
            row[f] = val
        writer.writerow(row)
    return output.getvalue()
