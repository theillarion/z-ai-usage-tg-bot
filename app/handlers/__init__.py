"""Handlers package with aggregated router."""

from aiogram import Router

from app.handlers.accounts import router as accounts_router
from app.handlers.alerts import router as alerts_router
from app.handlers.common import router as common_router


main_router = Router(name="main_router")
main_router.include_router(common_router)
main_router.include_router(accounts_router)
main_router.include_router(alerts_router)


def get_main_router() -> Router:
    """Return root router with reset parent_router for reattachment."""
    main_router._parent_router = None
    return main_router

