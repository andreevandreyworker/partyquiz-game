import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Player, Question, Reaction, Room, Vote


class GameRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_room(
        self, code: str, host_user_id: str, mode: str, categories: list
    ) -> Room:
        room = Room(
            code=code,
            host_user_id=host_user_id,
            mode=mode,
            categories=categories,
        )
        self._session.add(room)
        await self._session.flush()
        return room

    async def get_room(self, room_id: uuid.UUID) -> Room | None:
        return await self._session.get(Room, room_id)

    async def get_room_by_code(self, code: str) -> Room | None:
        return await self._session.scalar(
            select(Room).where(Room.code == code)
        )

    async def set_current_question(
        self, room_id: uuid.UUID, question_id: uuid.UUID | None
    ) -> None:
        room = await self._session.get(Room, room_id)
        if room:
            room.current_question_id = question_id

    async def set_status(self, room_id: uuid.UUID, status: str) -> None:
        room = await self._session.get(Room, room_id)
        if room:
            room.status = status

    async def set_phase(self, room_id: uuid.UUID, phase: str) -> None:
        room = await self._session.get(Room, room_id)
        if room:
            room.phase = phase

    async def add_player(
        self, room_id: uuid.UUID, user_id: str, login: str, is_host: bool
    ) -> Player:
        player = Player(
            room_id=room_id,
            user_id=user_id,
            login=login,
            is_host=is_host,
        )
        self._session.add(player)
        await self._session.flush()
        return player

    async def get_player(
        self, room_id: uuid.UUID, user_id: str
    ) -> Player | None:
        return await self._session.scalar(
            select(Player).where(
                Player.room_id == room_id, Player.user_id == user_id
            )
        )

    async def list_players(self, room_id: uuid.UUID) -> list[Player]:
        result = await self._session.scalars(
            select(Player)
            .where(Player.room_id == room_id)
            .order_by(Player.joined_at)
        )
        return list(result.all())

    async def remove_player(
        self, room_id: uuid.UUID, user_id: str
    ) -> None:
        await self._session.execute(
            delete(Player).where(
                Player.room_id == room_id, Player.user_id == user_id
            )
        )

    async def set_host(
        self, room_id: uuid.UUID, user_id: str
    ) -> None:
        player = await self.get_player(room_id, user_id)
        if player:
            player.is_host = True
        room = await self._session.get(Room, room_id)
        if room:
            room.host_user_id = user_id

    async def create_question(
        self,
        room_id: uuid.UUID,
        author_user_id: str | None,
        author_login: str | None,
        text: str,
        source: str,
    ) -> Question:
        question = Question(
            room_id=room_id,
            author_user_id=author_user_id,
            author_login=author_login,
            text=text,
            source=source,
        )
        self._session.add(question)
        await self._session.flush()
        return question

    async def get_question(
        self, question_id: uuid.UUID
    ) -> Question | None:
        return await self._session.get(Question, question_id)

    async def next_pending(
        self, room_id: uuid.UUID
    ) -> Question | None:
        return await self._session.scalar(
            select(Question)
            .where(
                Question.room_id == room_id,
                Question.status == "pending",
            )
            .order_by(Question.created_at)
            .limit(1)
        )

    async def set_question_status(
        self, question_id: uuid.UUID, status: str
    ) -> None:
        question = await self._session.get(Question, question_id)
        if question:
            question.status = status
            if status == "shown":
                question.shown_at = func.now()

    async def seconds_since_shown(
        self, question_id: uuid.UUID
    ) -> float | None:
        return await self._session.scalar(
            select(
                func.extract("epoch", func.now() - Question.shown_at)
            ).where(Question.id == question_id)
        )

    async def count_pending(self, room_id: uuid.UUID) -> int:
        return await self._session.scalar(
            select(func.count())
            .select_from(Question)
            .where(
                Question.room_id == room_id,
                Question.status == "pending",
            )
        ) or 0

    async def count_pending_by_user(
        self, room_id: uuid.UUID, user_id: str
    ) -> int:
        return await self._session.scalar(
            select(func.count())
            .select_from(Question)
            .where(
                Question.room_id == room_id,
                Question.author_user_id == user_id,
                Question.status == "pending",
            )
        ) or 0

    async def toggle_reaction(
        self, question_id: uuid.UUID, user_id: str
    ) -> int:
        existing = await self._session.scalar(
            select(Reaction).where(
                Reaction.question_id == question_id,
                Reaction.user_id == user_id,
            )
        )
        question = await self._session.get(Question, question_id)
        if existing:
            await self._session.delete(existing)
            if question and question.fire_count > 0:
                question.fire_count -= 1
        else:
            self._session.add(
                Reaction(question_id=question_id, user_id=user_id)
            )
            if question:
                question.fire_count += 1
        await self._session.flush()
        return question.fire_count if question else 0

    async def set_vote(
        self, question_id: uuid.UUID, user_id: str, choice: str
    ) -> None:
        existing = await self._session.scalar(
            select(Vote).where(
                Vote.question_id == question_id,
                Vote.user_id == user_id,
            )
        )
        if existing:
            existing.choice = choice
        else:
            self._session.add(
                Vote(
                    question_id=question_id,
                    user_id=user_id,
                    choice=choice,
                )
            )
        await self._session.flush()

    async def get_vote(
        self, question_id: uuid.UUID, user_id: str
    ) -> str | None:
        return await self._session.scalar(
            select(Vote.choice).where(
                Vote.question_id == question_id,
                Vote.user_id == user_id,
            )
        )

    async def count_votes(self, question_id: uuid.UUID) -> int:
        return await self._session.scalar(
            select(func.count())
            .select_from(Vote)
            .where(Vote.question_id == question_id)
        ) or 0

    async def tally(self, question_id: uuid.UUID) -> dict[str, int]:
        rows = await self._session.execute(
            select(Vote.choice, func.count())
            .where(Vote.question_id == question_id)
            .group_by(Vote.choice)
        )
        counts = {"norm": 0, "cringe": 0}
        for choice, n in rows.all():
            counts[choice] = n
        return counts
