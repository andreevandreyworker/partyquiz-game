import random
import string
import uuid

from app import gameconfig
from app.dto import (
    CreateRoomRequest,
    PlayerResponse,
    QuestionResponse,
    RoomResponse,
    SubmitQuestionRequest,
)
from app.exceptions import (
    EmptyQuestionError,
    NotHostError,
    NotInRoomError,
    RoomNotFoundError,
    TooManyPendingError,
)
from app.config import settings
from app.models import Question, Room
from app.realtime import realtime
from app.repositories import GameRepository


def _gen_code(length: int = 5) -> str:
    return "".join(
        random.choices(string.ascii_uppercase + string.digits, k=length)
    )


class GameController:
    def __init__(self, repo: GameRepository):
        self._repo = repo

    async def create_room(
        self,
        user_id: str,
        login: str,
        data: CreateRoomRequest,
        premium: bool = False,
    ) -> RoomResponse:
        categories = data.categories
        if not premium:
            premium_ids = await gameconfig.get_premium_ids()
            categories = [
                c for c in categories
                if c not in premium_ids
            ]
        length = await gameconfig.get_int("room_code_length", 5)
        code = _gen_code(length)
        while await self._repo.get_room_by_code(code):
            code = _gen_code(length)
        room = await self._repo.create_room(
            code, user_id, data.mode, categories
        )
        await self._repo.add_player(room.id, user_id, login, True)
        return await self._build(room, user_id)

    async def join_room(
        self, user_id: str, login: str, code: str
    ) -> RoomResponse:
        room = await self._repo.get_room_by_code(code.upper())
        if not room or room.status != "active":
            raise RoomNotFoundError()
        if not await self._repo.get_player(room.id, user_id):
            await self._repo.add_player(room.id, user_id, login, False)
            await realtime.publish(
                room.code,
                {"type": "player_joined", "login": login},
            )
        return await self._build(room, user_id)

    async def get_room(self, code: str, user_id: str) -> RoomResponse:
        room = await self._repo.get_room_by_code(code.upper())
        if not room:
            raise RoomNotFoundError()
        return await self._build(room, user_id)

    async def submit_statement(
        self,
        code: str,
        user_id: str,
        login: str,
        data: SubmitQuestionRequest,
    ) -> QuestionResponse:
        room = await self._require_membership(code, user_id)
        text = data.text.strip()
        if not text:
            raise EmptyQuestionError()
        pending = await self._repo.count_pending_by_user(
            room.id, user_id
        )
        max_pending = await gameconfig.get_int(
            "max_pending_per_user", settings.max_pending_per_user
        )
        if pending >= max_pending:
            raise TooManyPendingError()
        max_len = await gameconfig.get_int(
            "question_max_length", settings.question_max_length
        )
        statement = await self._repo.create_question(
            room.id,
            user_id,
            login,
            text[:max_len],
            "user",
        )
        await realtime.publish(
            room.code,
            {"type": "statement_queued", "author_login": login},
        )
        return self._question_dto(statement)

    async def advance(self, code: str, user_id: str) -> RoomResponse:
        room = await self._require_membership(code, user_id)
        if room.host_user_id != user_id:
            raise NotHostError()
        if room.phase == "voting":
            return await self._build(room, user_id)
        if room.current_question_id:
            await self._repo.set_question_status(
                room.current_question_id, "done"
            )
        nxt = await self._repo.next_pending(room.id)
        if nxt is None:
            nxt = await self._repo.create_question(
                room.id,
                None,
                None,
                await gameconfig.random_statement(room.categories),
                "bank",
            )
        await self._repo.set_question_status(nxt.id, "shown")
        await self._repo.set_current_question(room.id, nxt.id)
        await self._repo.set_phase(room.id, "voting")
        await realtime.publish(
            room.code,
            {
                "type": "statement_shown",
                "question": self._question_dto(nxt).model_dump(),
            },
        )
        return await self._build(room, user_id)

    async def reveal(self, code: str, user_id: str) -> RoomResponse:
        room = await self._require_membership(code, user_id)
        if room.host_user_id != user_id:
            raise NotHostError()
        if room.phase != "voting" or not room.current_question_id:
            return await self._build(room, user_id)
        await self._do_reveal(room)
        return await self._build(room, user_id)

    async def _do_reveal(self, room: Room) -> None:
        await self._repo.set_phase(room.id, "revealed")
        tally = await self._repo.tally(room.current_question_id)
        await realtime.publish(
            room.code,
            {
                "type": "revealed",
                "question_id": str(room.current_question_id),
                "tally": tally,
            },
        )

    async def vote(
        self, code: str, user_id: str, choice: str
    ) -> RoomResponse:
        room = await self._require_membership(code, user_id)
        if room.phase != "voting" or not room.current_question_id:
            return await self._build(room, user_id)
        await self._repo.set_vote(
            room.current_question_id, user_id, choice
        )
        voted = await self._repo.count_votes(room.current_question_id)
        await realtime.publish(
            room.code,
            {"type": "vote_progress", "voted_count": voted},
        )
        players = await self._repo.list_players(room.id)
        if voted >= len(players):
            await self._do_reveal(room)
        return await self._build(room, user_id)

    async def react(
        self, code: str, user_id: str, question_id: str
    ) -> int:
        room = await self._require_membership(code, user_id)
        count = await self._repo.toggle_reaction(
            uuid.UUID(question_id), user_id
        )
        await realtime.publish(
            room.code,
            {
                "type": "fire_update",
                "question_id": question_id,
                "fire_count": count,
            },
        )
        return count

    async def leave_room(self, code: str, user_id: str) -> None:
        room = await self._repo.get_room_by_code(code.upper())
        if not room:
            return
        await self._repo.remove_player(room.id, user_id)
        players = await self._repo.list_players(room.id)
        if not players:
            await self._repo.set_status(room.id, "closed")
            return
        if room.host_user_id == user_id:
            await self._repo.set_host(room.id, players[0].user_id)
            await realtime.publish(
                room.code,
                {"type": "host_changed", "login": players[0].login},
            )
        await realtime.publish(
            room.code, {"type": "player_left", "user_id": user_id}
        )
        if room.phase == "voting" and room.current_question_id:
            voted = await self._repo.count_votes(
                room.current_question_id
            )
            if voted >= len(players):
                await self._do_reveal(room)

    async def _require_membership(
        self, code: str, user_id: str
    ) -> Room:
        room = await self._repo.get_room_by_code(code.upper())
        if not room:
            raise RoomNotFoundError()
        if not await self._repo.get_player(room.id, user_id):
            raise NotInRoomError()
        return room

    async def _build(self, room: Room, user_id: str) -> RoomResponse:
        players = await self._repo.list_players(room.id)
        current = None
        voted_count = 0
        my_vote = None
        tally = None
        if room.current_question_id:
            q = await self._repo.get_question(room.current_question_id)
            if q:
                current = self._question_dto(q)
            voted_count = await self._repo.count_votes(
                room.current_question_id
            )
            my_vote = await self._repo.get_vote(
                room.current_question_id, user_id
            )
            if room.phase == "revealed":
                tally = await self._repo.tally(
                    room.current_question_id
                )
        pending_count = await self._repo.count_pending(room.id)
        return RoomResponse(
            id=str(room.id),
            code=room.code,
            mode=room.mode,
            status=room.status,
            phase=room.phase,
            categories=room.categories,
            host_user_id=room.host_user_id,
            players=[
                PlayerResponse(
                    user_id=p.user_id,
                    login=p.login,
                    is_host=p.is_host,
                )
                for p in players
            ],
            current_question=current,
            voted_count=voted_count,
            my_vote=my_vote,
            tally=tally,
            pending_count=pending_count,
        )

    def _question_dto(self, q: Question) -> QuestionResponse:
        return QuestionResponse(
            id=str(q.id),
            text=q.text,
            source=q.source,
            author_login=q.author_login,
            fire_count=q.fire_count,
        )
