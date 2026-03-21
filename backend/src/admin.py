from __future__ import annotations

import hmac
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import sqlalchemy as sa
from fastapi import FastAPI
from sqladmin import Admin, BaseView, ModelView, expose
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import func, select
from starlette.requests import Request

from src.config.settings import settings
from src.db.session import AsyncSessionLocal
from src.db.session import engine
from src.models.dating_room import DatingRoom
from src.models.dating_room_participant import DatingRoomParticipant
from src.models.date_idea import DateIdea
from src.models.user import User


logger = logging.getLogger(__name__)
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


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


class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"

    column_list = [
        User.id,
        User.name,
        User.created_at,
        User.deleted_at,
    ]
    column_searchable_list = [
        User.id,
        User.name,
    ]
    column_sortable_list = [
        User.id,
        User.name,
        User.created_at,
        User.deleted_at,
    ]
    form_columns = [
        User.id,
        User.name,
        User.deleted_at,
    ]
    column_default_sort = (User.created_at, True)
    page_size = 25


class AnalyticsAdmin(BaseView):
    name = "Статистика"
    identity = "analytics"
    icon = "fa-solid fa-chart-line"

    @staticmethod
    def _last_n_days(day_count: int, end_day: date) -> list[date]:
        start_day = end_day - timedelta(days=day_count - 1)
        return [start_day + timedelta(days=index) for index in range(day_count)]

    @staticmethod
    def _percent(part: int, total: int) -> float:
        if total == 0:
            return 0.0
        return round(part * 100 / total, 1)

    @staticmethod
    def _serialize_dates(days: list[date]) -> list[str]:
        return [day.isoformat() for day in days]

    @expose("/analytics", methods=["GET"], identity="analytics")
    async def analytics(self, request: Request):
        utc_now = datetime.now(UTC)
        today = utc_now.date()
        last_30_days = self._last_n_days(30, today)
        last_90_days = self._last_n_days(90, today)
        monday_this_week = today - timedelta(days=today.weekday())
        last_12_weeks = [monday_this_week - timedelta(weeks=offset) for offset in range(11, -1, -1)]

        day_30_start = datetime.combine(last_30_days[0], datetime.min.time(), tzinfo=UTC)
        day_90_start = datetime.combine(last_90_days[0], datetime.min.time(), tzinfo=UTC)
        week_12_start = datetime.combine(last_12_weeks[0], datetime.min.time(), tzinfo=UTC)
        day_7_start = utc_now - timedelta(days=7)
        day_30_start_dt = utc_now - timedelta(days=30)

        created_day = sa.cast(User.created_at, sa.Date)
        deleted_day = sa.cast(User.deleted_at, sa.Date)
        created_week = sa.cast(func.date_trunc("week", User.created_at), sa.Date)

        async with AsyncSessionLocal() as session:
            total_users = await session.scalar(select(func.count(User.id)))
            active_users = await session.scalar(
                select(func.count(User.id)).where(User.deleted_at.is_(None))
            )
            deleted_users = await session.scalar(
                select(func.count(User.id)).where(User.deleted_at.is_not(None))
            )
            new_users_7d = await session.scalar(
                select(func.count(User.id)).where(User.created_at >= day_7_start)
            )
            new_users_30d = await session.scalar(
                select(func.count(User.id)).where(User.created_at >= day_30_start_dt)
            )
            users_with_rooms = await session.scalar(
                select(func.count(sa.distinct(DatingRoomParticipant.user_id)))
            )
            rooms_created_30d = await session.scalar(
                select(func.count(DatingRoom.id)).where(DatingRoom.created_at >= day_30_start_dt)
            )
            matched_rooms_30d = await session.scalar(
                select(func.count(DatingRoom.id)).where(DatingRoom.matched_at >= day_30_start_dt)
            )

            registrations_rows = (
                await session.execute(
                    select(
                        created_day.label("day"),
                        func.count(User.id).label("count"),
                    )
                    .where(User.created_at >= day_30_start)
                    .group_by(created_day)
                    .order_by(created_day)
                )
            ).all()

            created_90_rows = (
                await session.execute(
                    select(
                        created_day.label("day"),
                        func.count(User.id).label("count"),
                    )
                    .where(User.created_at >= day_90_start)
                    .group_by(created_day)
                    .order_by(created_day)
                )
            ).all()

            deleted_90_rows = (
                await session.execute(
                    select(
                        deleted_day.label("day"),
                        func.count(User.id).label("count"),
                    )
                    .where(User.deleted_at.is_not(None), User.deleted_at >= day_90_start)
                    .group_by(deleted_day)
                    .order_by(deleted_day)
                )
            ).all()

            weekly_rows = (
                await session.execute(
                    select(
                        created_week.label("week"),
                        func.count(User.id).label("count"),
                    )
                    .where(User.created_at >= week_12_start)
                    .group_by(created_week)
                    .order_by(created_week)
                )
            ).all()

        total_users = int(total_users or 0)
        active_users = int(active_users or 0)
        deleted_users = int(deleted_users or 0)
        new_users_7d = int(new_users_7d or 0)
        new_users_30d = int(new_users_30d or 0)
        users_with_rooms = int(users_with_rooms or 0)
        rooms_created_30d = int(rooms_created_30d or 0)
        matched_rooms_30d = int(matched_rooms_30d or 0)

        registrations_map = {row.day: int(row.count) for row in registrations_rows}
        created_90_map = {row.day: int(row.count) for row in created_90_rows}
        deleted_90_map = {row.day: int(row.count) for row in deleted_90_rows}
        weekly_map = {row.week: int(row.count) for row in weekly_rows}

        registrations_daily = [registrations_map.get(day, 0) for day in last_30_days]
        created_daily_90 = [created_90_map.get(day, 0) for day in last_90_days]
        deleted_daily_90 = [deleted_90_map.get(day, 0) for day in last_90_days]

        running_active = active_users - sum(created_daily_90) + sum(deleted_daily_90)
        active_daily_90: list[int] = []
        for created_count, deleted_count in zip(created_daily_90, deleted_daily_90, strict=False):
            running_active += created_count
            running_active -= deleted_count
            active_daily_90.append(max(running_active, 0))

        weekly_registrations = [weekly_map.get(week_start, 0) for week_start in last_12_weeks]

        metrics = [
            {
                "label": "Всего пользователей",
                "value": total_users,
                "hint": "Все зарегистрированные аккаунты",
            },
            {
                "label": "Активные пользователи",
                "value": active_users,
                "hint": f"{self._percent(active_users, total_users)}% от общего числа",
            },
            {
                "label": "Новые за 7 дней",
                "value": new_users_7d,
                "hint": "Прирост за последнюю неделю",
            },
            {
                "label": "Новые за 30 дней",
                "value": new_users_30d,
                "hint": "Прирост за последние 30 дней",
            },
            {
                "label": "Удалённые пользователи",
                "value": deleted_users,
                "hint": f"{self._percent(deleted_users, total_users)}% от общего числа",
            },
            {
                "label": "Пользователи с комнатами",
                "value": users_with_rooms,
                "hint": f"{self._percent(users_with_rooms, total_users)}% вовлечены в rooms",
            },
            {
                "label": "Комнат создано за 30 дней",
                "value": rooms_created_30d,
                "hint": "Новые dating rooms",
            },
            {
                "label": "Матчей за 30 дней",
                "value": matched_rooms_30d,
                "hint": "Комнаты с найденной идеей",
            },
        ]

        context = {
            "title": "Статистика пользователей",
            "subtitle": "Прирост, активность и operational метрики",
            "metrics": metrics,
            "registrations_labels_json": json.dumps(self._serialize_dates(last_30_days), ensure_ascii=False),
            "registrations_values_json": json.dumps(registrations_daily),
            "active_labels_json": json.dumps(self._serialize_dates(last_90_days), ensure_ascii=False),
            "active_values_json": json.dumps(active_daily_90),
            "weekly_labels_json": json.dumps(self._serialize_dates(last_12_weeks), ensure_ascii=False),
            "weekly_values_json": json.dumps(weekly_registrations),
        }
        return await self.templates.TemplateResponse(request, "admin/analytics.html", context)


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
        templates_dir=str(TEMPLATES_DIR),
    )
    admin.add_view(AnalyticsAdmin)
    admin.add_view(DateIdeaAdmin)
    admin.add_view(UserAdmin)
