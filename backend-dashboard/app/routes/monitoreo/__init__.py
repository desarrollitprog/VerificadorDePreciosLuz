from fastapi import APIRouter
from .heartbeat import router as heartbeat_router
from .servers import router as servers_router
from .devices import router as devices_router
from .sync import router as sync_router

router = APIRouter(tags=["monitoreo"])
router.include_router(heartbeat_router)
router.include_router(servers_router)
router.include_router(devices_router)
router.include_router(sync_router)
