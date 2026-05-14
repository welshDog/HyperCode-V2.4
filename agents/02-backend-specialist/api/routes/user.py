
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class User(BaseModel):
    id: str
    name: str
    email: str
    avatar_url: str

@router.get("/user/{user_id}", response_model=User)
async def get_user(user_id: str):
    return {
        "id": user_id,
        "name": "Test User",
        "email": "test@hypercode.com",
        "avatar_url": "https://example.com/avatar.png"
    }
