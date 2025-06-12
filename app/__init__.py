from fastapi.responses import JSONResponse
from fastapi import Request
import traceback

from app.utils.loggers import error_logger
from app.extension import app

"""
    Routers
"""


from app.routers.blocks_router import router as blocks_router
from app.routers.transactions_router import router as transactions_router
from app.routers.address_router import router as address_router
from app.routers.auth_router import router as auth_router

# from app.routers.user_router import router as user_router


app.include_router(auth_router)
# app.include_router(user_router)
app.include_router(address_router)
app.include_router(transactions_router)
app.include_router(blocks_router)


@app.middleware("http")
async def error_logging_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_logger.error(
            f"Erro não tratado: {str(e)}\n"
            f"Método: {request.method}\n"
            f"URL: {request.url}\n"
            f"Headers: {dict(request.headers)}\n"
            f"Stack trace:\n{traceback.format_exc()}"
        )

        return JSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )
