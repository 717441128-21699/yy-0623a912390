from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class CalculationTask(Base):
    __tablename__ = "calculation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(64), unique=True, index=True, nullable=False)
    project_id = Column(String(64), index=True, nullable=False)
    project_name = Column(String(256), nullable=False)
    building = Column(String(64), nullable=False)
    floor = Column(String(64), nullable=False)
    location = Column(String(256), nullable=False)
    element_type = Column(String(32), nullable=False)
    formwork_type = Column(String(32), nullable=False)
    support_height = Column(Float, nullable=False)
    element_length = Column(Float, nullable=True)
    element_width = Column(Float, nullable=True)
    element_height = Column(Float, nullable=True)
    slab_thickness = Column(Float, nullable=True)
    panel_material = Column(String(64), nullable=False)
    panel_thickness = Column(Float, nullable=False)
    secondary_beam_material = Column(String(64), nullable=False)
    secondary_beam_size = Column(String(64), nullable=False)
    secondary_beam_spacing = Column(Float, nullable=False)
    main_beam_material = Column(String(64), nullable=False)
    main_beam_size = Column(String(64), nullable=False)
    main_beam_spacing = Column(Float, nullable=False)
    pole_type = Column(String(64), nullable=False)
    pole_spacing_transverse = Column(Float, nullable=False)
    pole_spacing_longitudinal = Column(Float, nullable=False)
    horizontal_step = Column(Float, nullable=False)
    construction_load = Column(Float, nullable=True)
    status = Column(String(32), default="pending")
    overall_risk_level = Column(String(32), nullable=True)
    pass_status = Column(String(32), nullable=True)
    failure_reasons = Column(JSON, nullable=True)
    submitted_by = Column(String(128), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    remark = Column(Text, nullable=True)

    results = relationship("CheckResult", back_populates="task", cascade="all, delete-orphan")
    voucher = relationship("CalculationVoucher", back_populates="task", uselist=False, cascade="all, delete-orphan")


class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("calculation_tasks.id"), nullable=False)
    check_item = Column(String(64), nullable=False)
    check_item_name = Column(String(128), nullable=False)
    calculated_value = Column(Float, nullable=False)
    allowable_value = Column(Float, nullable=False)
    ratio = Column(Float, nullable=False)
    is_passed = Column(Integer, default=1)
    risk_level = Column(String(32), nullable=False)
    detail = Column(JSON, nullable=True)

    task = relationship("CalculationTask", back_populates="results")


class CalculationVoucher(Base):
    __tablename__ = "calculation_vouchers"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("calculation_tasks.id"), unique=True, nullable=False)
    voucher_code = Column(String(64), unique=True, index=True, nullable=False)
    input_params = Column(JSON, nullable=False)
    calculation_process = Column(JSON, nullable=False)
    conclusion = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("CalculationTask", back_populates="voucher")
