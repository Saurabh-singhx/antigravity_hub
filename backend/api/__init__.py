from .routes_system import router as system_router
from .routes_notifications import router as notifications_router
from .routes_qna import router as qna_router

__all__ = ["system_router", "notifications_router", "qna_router"]
