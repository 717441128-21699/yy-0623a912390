from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import api_router
from app.config import API_V1_PREFIX

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="模板支撑验算后端服务",
    description="面向项目管理平台、BIM看板或企业安全系统调用的模板支撑统一验算服务。"
                "支持提交验算任务、返回风险结论、留存计算凭证三大核心能力。",
    version="1.0.0",
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

app.include_router(api_router)


@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "formwork-check-service"}


@app.get("/", summary="服务信息")
async def root():
    return {
        "name": "模板支撑验算后端服务",
        "version": "1.0.0",
        "status": "running",
        "api_docs": "/docs",
        "api_prefix": API_V1_PREFIX
    }
