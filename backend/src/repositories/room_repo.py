from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import and_, func, insert, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.date_idea import DateIdea
from src.models.dating_room import DatingRoom
from src.models.dating_room_memory import DatingRoomMemory
from src.models.dating_room_participant import DatingRoomParticipant
from src.models.dating_room_swipe import DatingRoomSwipe
from src.models.user import User


DEFAULT_DATE_IDEAS = [
    {
        "title": "Coffee Walk Challenge",
        "description": "Take coffee to go, pick a district, and each of you chooses one spontaneous stop on the route.",
        "category": "City",
        "vibe": "Easygoing",
    },
    {
        "title": "Museum With a Game",
        "description": "Visit a museum and invent awards for the most dramatic, weirdest, and most underrated exhibit.",
        "category": "Culture",
        "vibe": "Curious",
    },
    {
        "title": "Sunset Picnic",
        "description": "Build a small picnic with snacks, a blanket, and a playlist, then rate the sunset like harsh critics.",
        "category": "Outdoor",
        "vibe": "Romantic",
    },
    {
        "title": "Street Food Tour",
        "description": "Pick three unfamiliar places and split one item at each stop so you discover new favorites together.",
        "category": "Food",
        "vibe": "Playful",
    },
    {
        "title": "Bookstore Date",
        "description": "Meet in a bookstore, choose a book for each other under a budget, and explain the pick over tea.",
        "category": "Indoor",
        "vibe": "Warm",
    },
    {
        "title": "Arcade Night",
        "description": "Play a few ridiculous games, keep score, and let the loser choose the post-game dessert spot.",
        "category": "Fun",
        "vibe": "Competitive",
    },
]


class RoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_default_ideas(self) -> None:
        ideas_count = await self.session.scalar(select(func.count(DateIdea.id)))
        if ideas_count:
            return

        await self.session.execute(insert(DateIdea), DEFAULT_DATE_IDEAS)
        await self.session.commit()

    async def create_room(self, *, creator_user_id: int) -> DatingRoom:
        room = DatingRoom(creator_user_id=creator_user_id)
        self.session.add(room)
        await self.session.flush()

        participant_stmt = (
            pg_insert(DatingRoomParticipant)
            .values(room_id=room.id, user_id=creator_user_id)
            .on_conflict_do_nothing(index_elements=[DatingRoomParticipant.room_id, DatingRoomParticipant.user_id])
        )
        await self.session.execute(participant_stmt)
        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def get_room(self, room_id: UUID) -> DatingRoom | None:
        return await self.session.get(DatingRoom, room_id)

    async def get_rooms_for_user(self, user_id: int) -> list[DatingRoom]:
        stmt = (
            select(DatingRoom)
            .join(DatingRoomParticipant, DatingRoomParticipant.room_id == DatingRoom.id)
            .where(DatingRoomParticipant.user_id == user_id)
            .order_by(DatingRoom.updated_at.desc(), DatingRoom.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_latest_matched_room_for_photo(self, user_id: int) -> DatingRoom | None:
        latest_stmt = (
            select(DatingRoom)
            .join(DatingRoomParticipant, DatingRoomParticipant.room_id == DatingRoom.id)
            .where(
                DatingRoomParticipant.user_id == user_id,
                DatingRoom.status == "matched",
            )
            .order_by(DatingRoom.matched_at.desc().nullslast(), DatingRoom.updated_at.desc())
            .limit(1)
        )
        return await self.session.scalar(latest_stmt)

    async def get_room_participants(self, room_id: UUID) -> list[tuple[int, str]]:
        stmt = (
            select(User.id, User.name)
            .join(DatingRoomParticipant, DatingRoomParticipant.user_id == User.id)
            .where(DatingRoomParticipant.room_id == room_id)
            .order_by(DatingRoomParticipant.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_room_memories(self, room_id: UUID) -> list[tuple[DatingRoomMemory, str]]:
        stmt = (
            select(DatingRoomMemory, User.name)
            .join(User, User.id == DatingRoomMemory.uploaded_by_user_id)
            .where(DatingRoomMemory.room_id == room_id)
            .order_by(DatingRoomMemory.created_at.desc(), DatingRoomMemory.id.desc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_room_memory(self, memory_id: int) -> tuple[DatingRoomMemory, str] | None:
        stmt = (
            select(DatingRoomMemory, User.name)
            .join(User, User.id == DatingRoomMemory.uploaded_by_user_id)
            .where(DatingRoomMemory.id == memory_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    async def is_participant(self, room_id: UUID, user_id: int) -> bool:
        stmt = select(literal(True)).where(
            and_(
                DatingRoomParticipant.room_id == room_id,
                DatingRoomParticipant.user_id == user_id,
            )
        )
        return bool(await self.session.scalar(stmt))

    async def add_participant(self, room_id: UUID, user_id: int) -> bool:
        participants = await self.get_room_participants(room_id)
        if len(participants) >= 2 and user_id not in {participant_id for participant_id, _ in participants}:
            return False

        stmt = (
            pg_insert(DatingRoomParticipant)
            .values(room_id=room_id, user_id=user_id)
            .on_conflict_do_nothing(index_elements=[DatingRoomParticipant.room_id, DatingRoomParticipant.user_id])
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def remove_participant(self, room_id: UUID, user_id: int) -> None:
        await self.session.execute(
            sa.delete(DatingRoomParticipant).where(
                DatingRoomParticipant.room_id == room_id,
                DatingRoomParticipant.user_id == user_id,
            )
        )
        await self.session.commit()

    async def delete_room(self, room_id: UUID) -> None:
        await self.session.execute(sa.delete(DatingRoom).where(DatingRoom.id == room_id))
        await self.session.commit()

    async def add_room_memory(
        self,
        room_id: UUID,
        *,
        uploaded_by_user_id: int,
        photo_key: str,
        postcard_key: str,
        matched_at: datetime | None,
    ) -> DatingRoomMemory:
        room = await self.get_room(room_id)
        if room is None:
            raise ValueError("Room not found")

        memory = DatingRoomMemory(
            room_id=room_id,
            uploaded_by_user_id=uploaded_by_user_id,
            photo_key=photo_key,
            postcard_key=postcard_key,
            matched_at=matched_at,
        )
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def mark_room_revealed(self, room_id: UUID) -> DatingRoom | None:
        room = await self.get_room(room_id)
        if room is None:
            return None

        if room.match_revealed_at is None:
            room.match_revealed_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(room)
        return room

    async def set_room_status(self, room_id: UUID, status: str, matched_idea_id: int | None = None) -> None:
        room = await self.get_room(room_id)
        if room is None:
            return

        room.status = status
        if matched_idea_id is not None:
            room.matched_idea_id = matched_idea_id
        if status == "matched":
            room.matched_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(room)

    async def get_idea(self, idea_id: int) -> DateIdea | None:
        return await self.session.get(DateIdea, idea_id)

    async def get_next_unswiped_idea(self, room_id: UUID, user_id: int) -> DateIdea | None:
        subquery = (
            select(DatingRoomSwipe.idea_id)
            .where(
                DatingRoomSwipe.room_id == room_id,
                DatingRoomSwipe.user_id == user_id,
            )
            .subquery()
        )
        # Keep a stable but different deck order for each user inside each room.
        shuffle_key = func.md5(
            func.concat(
                sa.literal(str(room_id)),
                ":",
                sa.literal(str(user_id)),
                ":",
                func.cast(DateIdea.id, sa.Text),
            )
        )
        stmt = (
            select(DateIdea)
            .where(~DateIdea.id.in_(select(subquery.c.idea_id)))
            .order_by(shuffle_key.asc(), DateIdea.id.asc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def save_swipe(self, room_id: UUID, user_id: int, idea_id: int, liked: bool) -> None:
        stmt = (
            pg_insert(DatingRoomSwipe)
            .values(room_id=room_id, user_id=user_id, idea_id=idea_id, liked=liked)
            .on_conflict_do_update(
                index_elements=[
                    DatingRoomSwipe.room_id,
                    DatingRoomSwipe.user_id,
                    DatingRoomSwipe.idea_id,
                ],
                set_={"liked": liked},
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def count_room_participants(self, room_id: UUID) -> int:
        stmt = select(func.count()).select_from(DatingRoomParticipant).where(DatingRoomParticipant.room_id == room_id)
        count = await self.session.scalar(stmt)
        return int(count or 0)

    async def get_match_for_idea(self, room_id: UUID, idea_id: int) -> bool:
        stmt = (
            select(func.count(func.distinct(DatingRoomSwipe.user_id)))
            .where(
                DatingRoomSwipe.room_id == room_id,
                DatingRoomSwipe.idea_id == idea_id,
                DatingRoomSwipe.liked.is_(True),
            )
        )
        liked_count = await self.session.scalar(stmt)
        return int(liked_count or 0) >= 2
