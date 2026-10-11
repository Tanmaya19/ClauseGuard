"""Aggregate router for API v1."""

from fastapi import APIRouter

from app.api.v1 import auth, contracts, health, reports

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router)
api_router.include_router(contracts.router)
api_router.include_router(reports.router)
