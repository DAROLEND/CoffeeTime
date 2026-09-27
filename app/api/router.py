"""Assembles every router under `/api`.

`api_router` carries the CSRF dependency, so every mutating endpoint is
protected unless it is deliberately mounted on `webhook_router` instead
(only the two LiqPay endpoints that LiqPay itself calls).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.routers.public import auth, cart, checkout, menu, pages, payments, profile, reviews, session
from app.schemas.common import ErrorResponse
from app.services.csrf import verify_csrf

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Validation or business-rule error"},
    401: {"model": ErrorResponse, "description": "Not logged in"},
    403: {"model": ErrorResponse, "description": "CSRF check failed or permission denied"},
    404: {"model": ErrorResponse, "description": "Not found"},
}

api_router = APIRouter(prefix="/api", dependencies=[Depends(verify_csrf)], responses=ERROR_RESPONSES)
for module in (session, pages, menu, cart, checkout, payments, auth, profile, reviews):
    api_router.include_router(module.router)

webhook_router = APIRouter(prefix="/api")
webhook_router.include_router(payments.webhook_router)
