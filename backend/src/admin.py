from __future__ import annotations

import hmac
import logging

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.config.settings import settings
from src.db.session import engine
from src.models.date_idea import DateIdea


logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):
    def __init__(self) -> None:
        super().__init__(secret_key=settings.JWT_SECRET.get_secret_value())

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        expected_username = settings.ADMIN_USERNAME
        expected_password = settings.ADMIN_PASSWORD.get_secret_value() if settings.ADMIN_PASSWORD else None
        if expected_username is None or expected_password is None:
            return False

        if not (
            hmac.compare_digest(username, expected_username)
            and hmac.compare_digest(password, expected_password)
        ):
            return False

        request.session.update({"admin_authenticated": True})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_authenticated"))


class DateIdeaAdmin(ModelView, model=DateIdea):
    name = "Идея"
    name_plural = "Идеи для свиданий"
    icon = "fa-solid fa-lightbulb"

    column_list = [
        DateIdea.id,
        DateIdea.title,
        DateIdea.category,
        DateIdea.vibe,
    ]
    column_searchable_list = [
        DateIdea.title,
        DateIdea.description,
        DateIdea.category,
        DateIdea.vibe,
    ]
    column_sortable_list = [
        DateIdea.id,
        DateIdea.title,
        DateIdea.category,
        DateIdea.vibe,
    ]
    form_columns = [
        DateIdea.title,
        DateIdea.description,
        DateIdea.category,
        DateIdea.vibe,
    ]
    column_default_sort = (DateIdea.id, True)
    page_size = 25


def setup_admin(app: FastAPI) -> None:
    if settings.ADMIN_USERNAME is None or settings.ADMIN_PASSWORD is None:
        logger.warning("SQLAdmin is disabled because ADMIN_USERNAME or ADMIN_PASSWORD is not configured.")
        return

    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=AdminAuth(),
        base_url="/admin",
        title="This Is It Admin",
    )
    admin.add_view(DateIdeaAdmin)
