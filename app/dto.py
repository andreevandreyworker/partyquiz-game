from pydantic import BaseModel, Field


class CreateRoomRequest(BaseModel):
    mode: str = Field(default="multi", pattern="^(multi|solo)$")
    categories: list[str] = Field(default_factory=list)


class JoinRoomRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class SubmitQuestionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=512)


class VoteRequest(BaseModel):
    choice: str = Field(pattern="^(norm|cringe)$")


class PlayerResponse(BaseModel):
    user_id: str
    login: str
    is_host: bool


class QuestionResponse(BaseModel):
    id: str
    text: str
    source: str
    author_login: str | None
    fire_count: int


class RoomResponse(BaseModel):
    id: str
    code: str
    mode: str
    status: str
    phase: str
    categories: list[str]
    host_user_id: str
    players: list[PlayerResponse]
    current_question: QuestionResponse | None
    voted_count: int
    my_vote: str | None
    tally: dict[str, int] | None
    pending_count: int


class CategoryResponse(BaseModel):
    id: str
    ru: str
    en: str
    premium: bool = False
