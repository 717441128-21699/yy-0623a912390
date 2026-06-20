from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


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


class FormworkTaskListResponse(BaseModel):
    total: int
    items: List[Dict[str, Any]]


class ValidationErrorResponse(BaseModel):
    code: str = "validation_error"
    message: str
    missing_params: List[Dict[str, str]]


class VoucherResponse(BaseModel):
    task_id: int
    voucher_code: str
    input_params: Dict[str, Any]
    calculation_process: Dict[str, Any]
    conclusion: str
    created_at: datetime
