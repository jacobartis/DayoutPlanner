import pymongo
import datetime

# Replace with your MongoDB Atlas connection string
mongo_uri = "mongodb+srv://dayoutplanner:nopassword@cluster0.wd4xi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB Atlas
client = pymongo.MongoClient(mongo_uri)

class User:
    name = ""
    lobby_id = None
    is_host = False
    def __init__(self,name):
        self.name = name
    
    def create_lobby(self)->str:
        if not self.lobby_id is None: return self.lobby_id

        # Access a database and collection
        db = client["mydatabase"]
        collection = db["open_lobbies"]

        # Insert a document
        self.lobby_id = str(abs(hash(datetime.datetime.now())))[:6]
        lobby_info ={
            "lobby_id":self.lobby_id,
            "users":[self.name]
        }
        collection.insert_one(lobby_info)
        self.is_host = True
        return self.lobby_id

    def join_lobby(self,lobby_id:str):
        if not self.lobby_id is None: return False
        db = client["mydatabase"]
        collection = db["open_lobbies"]
        retrieved_lobby = collection.find_one({"lobby_id":lobby_id})
        if retrieved_lobby is None: return False
        collection.update_one({"lobby_id":lobby_id},
                              {"$addToSet":{"users":self.name}})
        self.lobby_id = lobby_id
        return True

    def leave_lobby(self):
        if not self.lobby_id is None: return False
        db = client["mydatabase"]
        collection = db["open_lobbies"]
        retrieved_lobby = collection.find_one({"lobby_id":self.lobby_id})
        if retrieved_lobby is None: return False
        collection.update_one({"lobby_id":self.lobby_id},
                              {"$pull":{"users":self.name}})
        if self.is_host:
            collection.delete_one({"lobby_id":self.lobby_id})
            self.is_host = False
        self.lobby_id = None
        return True

host = User("Cool guy")
id = host.create_lobby()
user = User("Other guy")
user.join_lobby(id)
# db = client["mydatabase"]
# collection = db["active_lobbies"]

# # Insert a document
# id = str(abs(hash(datetime.datetime.now())))[:6]
# lobby_info ={
#     "lobby_id":id, 
#     "user":{"id":1,"name":"Testname"},
#     "likes":[]
# }
# collection.insert_one(lobby_info)

# # Fetch a document
# #retrieved_user = collection.find_one({"name": "Alice"})
# #print(retrieved_user)