from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import engine, Base
from app.routers import api_router
from app.config import API_V1_PREFIX
from app.schemas import unified_validation_exception_handler
from app.exceptions import BusinessValidationError
import app.models


async def business_validation_error_handler(request: Request, exc: BusinessValidationError):
    content = {
        "code": exc.code,
        "message": exc.message,
    }
    if exc.missing_params:
        content["missing_params"] = exc.missing_params
    if exc.detail:
        content["detail"] = exc.detail
    return JSONResponse(status_code=400, content=content)


app = FastAPI(
    title="模板支撑验算后端服务",
    description="面向项目管理平台、BIM看板或企业安全系统调用的模板支撑统一验算服务。"
                "支持提交验算任务、返回风险结论、留存计算凭证三大核心能力。",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, unified_validation_exception_handler)
app.add_exception_handler(BusinessValidationError, business_validation_error_handler)

app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)


@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "formwork-check-service", "version": "2.0.0"}


@app.get("/", summary="服务信息")
async def root():
    return {
        "name": "模板支撑验算后端服务",
        "version": "2.0.0",
        "status": "running",
        "api_docs": "/docs",
        "api_prefix": API_V1_PREFIX
    }
