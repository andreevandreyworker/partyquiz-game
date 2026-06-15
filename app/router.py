from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.categories import CATEGORIES
from app.controllers import GameController
from app.dependencies import (
    CurrentUser,
    decode_token,
    get_controller,
    get_current_user,
)
from app.dto import (
    CategoryResponse,
    CreateRoomRequest,
    JoinRoomRequest,
    QuestionResponse,
    RoomResponse,
    SubmitQuestionRequest,
    VoteRequest,
)
from app.realtime import realtime

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def categories() -> list[CategoryResponse]:
    return [CategoryResponse(**c) for c in CATEGORIES]


@router.post("/rooms", response_model=RoomResponse)
async def create_room(
    data: CreateRoomRequest,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> RoomResponse:
    return await controller.create_room(
        user.user_id, user.login, data, user.premium
    )


@router.post("/rooms/join", response_model=RoomResponse)
async def join_room(
    data: JoinRoomRequest,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> RoomResponse:
    return await controller.join_room(
        user.user_id, user.login, data.code
    )


@router.get("/rooms/{code}", response_model=RoomResponse)
async def get_room(
    code: str,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> RoomResponse:
    return await controller.get_room(code, user.user_id)


@router.post(
    "/rooms/{code}/statements", response_model=QuestionResponse
)
async def submit_statement(
    code: str,
    data: SubmitQuestionRequest,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> QuestionResponse:
    return await controller.submit_statement(
        code, user.user_id, user.login, data
    )


@router.post("/rooms/{code}/advance", response_model=RoomResponse)
async def advance(
    code: str,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> RoomResponse:
    return await controller.advance(code, user.user_id)


@router.post("/rooms/{code}/reveal", response_model=RoomResponse)
async def reveal(
    code: str,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> RoomResponse:
    return await controller.reveal(code, user.user_id)


@router.post("/rooms/{code}/vote", response_model=RoomResponse)
async def vote(
    code: str,
    data: VoteRequest,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> RoomResponse:
    return await controller.vote(code, user.user_id, data.choice)


@router.post("/rooms/{code}/statements/{question_id}/fire")
async def react(
    code: str,
    question_id: str,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> dict:
    count = await controller.react(code, user.user_id, question_id)
    return {"fire_count": count}


@router.post("/rooms/{code}/leave")
async def leave_room(
    code: str,
    user: CurrentUser = Depends(get_current_user),
    controller: GameController = Depends(get_controller),
) -> dict:
    await controller.leave_room(code, user.user_id)
    return {"status": "ok"}


@router.websocket("/ws/{code}")
async def ws_room(
    websocket: WebSocket, code: str, token: str = ""
) -> None:
    user = decode_token(token)
    if user is None:
        await websocket.close(code=4401)
        return
    code = code.upper()
    await realtime.connect(code, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime.disconnect(code, websocket)
