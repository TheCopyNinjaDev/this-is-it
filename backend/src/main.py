from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.admin import setup_admin
from src.api.deps import require_bearer_token
from src.api.v1.private.auth import router as auth_router
from src.api.v1.private.room import router as room_router
from src.api.v1.private.user import router as user_router
from src.config.settings import settings
from src import proxy_state

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET.get_secret_value(),
)

app.include_router(auth_router)
app.include_router(room_router)
app.include_router(user_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_admin(app)


@app.put("/internal/proxy-pool", dependencies=[Depends(require_bearer_token)])
async def update_proxy_pool(urls: list[str]) -> dict:
    proxy_state.set_proxy_urls(urls)
    return {"count": len(urls)}
