from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from pymongo import MongoClient

app = FastAPI(title="Day Out Planner API")

# MongoDB connection
mongo_uri = "mongodb+srv://dayoutplanner:newcoolpassword@cluster0.wd4xi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_uri)
db = client.dayoutplanner

# Pydantic Models
class Place(BaseModel):
    place_id: str
    name: str
    address: str
    rating: Optional[float]
    photo_reference: Optional[str]
    types: List[str]
    price_level: Optional[int]

class PreferenceOption(BaseModel):
    name: str
    type: str
    keyword: str

class CategoryMatch(BaseModel):
    category_name: str
    place: Dict
    matched_users: List[str]

class LobbyUser(BaseModel):
    user_id: str
    status: str = "active"  # active, kicked, left
    joined_at: datetime = Field(default_factory=datetime.now)

class Lobby(BaseModel):
    host_id: str
    location: str
    preferences: Dict
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "active"
    matches: List[CategoryMatch] = []
    current_category: str = ""
    users: List[LobbyUser] = []

class UserVote(BaseModel):
    user_id: str
    place_id: str
    place_details: Dict
    vote: bool
    category: str

class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str

# API Endpoints
@app.post("/lobbies/create", response_model=Lobby)
async def create_lobby(lobby_data: Lobby):
    """Create a new lobby with preferences"""
    lobby_id = str(uuid.uuid4())
    lobby_data.current_category = list(lobby_data.preferences.keys())[0] if lobby_data.preferences else ""
    lobby_data_dict = lobby_data.dict()
    lobby_data_dict["lobby_id"] = lobby_id
    db.lobbies.insert_one(lobby_data_dict)
    return lobby_data_dict

@app.get("/lobbies/{lobby_id}")
async def get_lobby(lobby_id: str):
    """Get lobby details"""
    lobby = db.lobbies.find_one({"lobby_id": lobby_id})
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    return lobby

@app.post("/lobbies/{lobby_id}/join")
async def join_lobby(lobby_id: str, user_id: str):
    """Join a lobby"""
    lobby = db.lobbies.find_one({"lobby_id": lobby_id})
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    existing_user = next((user for user in lobby.get("users", []) if user["user_id"] == user_id), None)
    if existing_user:
        if existing_user["status"] == "kicked":
            raise HTTPException(status_code=403, detail="You have been kicked from this lobby")
        return {"message": "Already in lobby"}

    db.lobbies.update_one({"lobby_id": lobby_id}, {"$push": {"users": LobbyUser(user_id=user_id).dict()}})
    return {"message": "Successfully joined lobby"}

@app.post("/lobbies/{lobby_id}/kick")
async def kick_user(lobby_id: str, host_id: str, user_id: str):
    """Kick a user from the lobby (host only)"""
    lobby = db.lobbies.find_one({"lobby_id": lobby_id})
    if not lobby or lobby["host_id"] != host_id:
        raise HTTPException(status_code=403, detail="Only the host can kick users")
    if user_id == host_id:
        raise HTTPException(status_code=400, detail="Cannot kick the host")

    db.lobbies.update_one({"lobby_id": lobby_id, "users.user_id": user_id}, {"$set": {"users.$.status": "kicked"}})
    db.votes.delete_many({"lobby_id": lobby_id, "user_id": user_id})
    db.lobbies.update_one({"lobby_id": lobby_id}, {"$pull": {"matches.$[].matched_users": user_id}})

    return {"message": "User kicked from lobby"}

@app.post("/lobbies/{lobby_id}/leave")
async def leave_lobby(lobby_id: str, user_id: str):
    """Voluntarily leave a lobby"""
    lobby = db.lobbies.find_one({"lobby_id": lobby_id})
    if not lobby or user_id == lobby["host_id"]:
        raise HTTPException(status_code=400, detail="Host cannot leave lobby. Delete lobby instead.")

    db.lobbies.update_one({"lobby_id": lobby_id, "users.user_id": user_id}, {"$set": {"users.$.status": "left"}})
    db.votes.delete_many({"lobby_id": lobby_id, "user_id": user_id})
    db.lobbies.update_one({"lobby_id": lobby_id}, {"$pull": {"matches.$[].matched_users": user_id}})

    return {"message": "Successfully left lobby"}

@app.delete("/lobbies/{lobby_id}")
async def delete_lobby(lobby_id: str, host_id: str):
    """Delete a lobby (host only)"""
    lobby = db.lobbies.find_one({"lobby_id": lobby_id})
    if not lobby or lobby["host_id"] != host_id:
        raise HTTPException(status_code=403, detail="Only the host can delete the lobby")

    db.votes.delete_many({"lobby_id": lobby_id})
    db.lobbies.delete_one({"lobby_id": lobby_id})

    return {"message": "Lobby deleted successfully"}

@app.get("/lobbies/{lobby_id}/matches")
async def get_lobby_matches(lobby_id: str):
    """Get all matches for a lobby"""
    lobby = db.lobbies.find_one({"lobby_id": lobby_id})
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    return lobby.get("matches", [])

def check_for_match(lobby_id: str, vote: UserVote):
    """Check if a place has enough likes to be considered a match."""
    if not vote.vote:
        return {"status": "vote_recorded"}

    positive_votes = list(db.votes.find({
        "lobby_id": lobby_id,
        "place_id": vote.place_id,
        "vote": True,
        "category": vote.category
    }))

    if len(positive_votes) >= 2:
        match = CategoryMatch(
            category_name=vote.category,
            place=vote.place_details,
            matched_users=[v["user_id"] for v in positive_votes]
        )

        lobby = db.lobbies.find_one({"lobby_id": lobby_id})
        categories = list(lobby["preferences"].keys())
        current_index = categories.index(vote.category)
        next_category = categories[current_index + 1] if current_index + 1 < len(categories) else None

        db.lobbies.update_one(
            {"lobby_id": lobby_id},
            {
                "$push": {"matches": match.dict()},
                "$set": {
                    "current_category": next_category,
                    "status": "completed" if next_category is None else "active"
                }
            }
        )

        return {"status": "matched", "match": match.dict(), "next_category": next_category}

    return {"status": "vote_recorded"}

# API Endpoints
@app.post("/lobbies/{lobby_id}/vote")
async def submit_vote(lobby_id: str, vote: UserVote):
    """Submit a vote and check for a match."""
    vote_data = vote.dict()
    vote_data["lobby_id"] = lobby_id
    vote_data["timestamp"] = datetime.now()

    db.votes.insert_one(vote_data)
    return check_for_match(lobby_id, vote)

@app.post("/users/create")
async def create_user(username: str):
    """Create a new user with a random ID."""
    user = User(username=username)
    db.users.insert_one(user.dict())
    return user
