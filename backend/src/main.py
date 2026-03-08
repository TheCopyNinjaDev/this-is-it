from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.private.auth import router as auth_router
from src.api.v1.private.room import router as room_router
from src.api.v1.private.user import router as user_router

app = FastAPI()

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
