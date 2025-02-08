import pymongo
import datetime

mongo_data = open("mongo_data.txt").read()
print(mongo_data)
# Replace with your MongoDB Atlas connection string
mongo_uri = "mongodb+srv://{mongo_data}@cluster0.wd4xi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB Atlas
client = pymongo.MongoClient(mongo_uri)

class User:
    name = ""
    user_id = 0
    lobby_id = None
    is_host = False
    def __init__(self,name):
        self.name = name
        self.user_id = abs(hash(self.name+str(datetime.datetime.microsecond)))

    def is_in_lobby(self):
        if self.lobby_id is None: return False
        db = client["mydatabase"]
        open_l = db["open_lobbies"]
        retrieved_open = open_l.find_one({"lobby_id":self.lobby_id})
        active_l = db["active_lobbies"]
        retrieved_active = active_l.find_one({"lobby_id":self.lobby_id})
        if retrieved_open is None and retrieved_active is None: return False
        return True

    def create_lobby(self)->str:
        if self.is_in_lobby(): return self.lobby_id

        # Access a database and collection
        db = client["mydatabase"]
        collection = db["open_lobbies"]

        # Insert a document
        self.lobby_id = str(abs(hash(self.name.capitalize()+str(datetime.datetime.now()))))[:6]
        lobby_info ={
            "lobby_id":self.lobby_id,
            "users":[{"user_id":self.user_id,
                      "name":self.name}]
        }
        collection.insert_one(lobby_info)
        self.is_host = True
        return self.lobby_id

    def join_lobby(self,lobby_id:str):
        if self.is_in_lobby(): return False
        db = client["mydatabase"]
        collection = db["open_lobbies"]
        retrieved_lobby = collection.find_one({"lobby_id":lobby_id})
        if retrieved_lobby is None: return False
        collection.update_one({"lobby_id":lobby_id},
                              {"$addToSet":{"users":{"user_id":self.user_id,
                                                    "name":self.name}}})
        self.lobby_id = lobby_id
        return True

    def leave_lobby(self):
        if not self.is_in_lobby(): return False
        db = client["mydatabase"]
        collection = db["open_lobbies"]#
        collection.update_one({"lobby_id":self.lobby_id},
                              {"$pull":{"users":self.name}})
        if self.is_host:
            collection.delete_one({"lobby_id":self.lobby_id})
            self.is_host = False
        self.lobby_id = None
        return True
    
    def start_lobby(self):
        if not self.is_host: 
            print("Not Host")
            return False
        if not self.is_in_lobby(): return False
        db = client["mydatabase"]
        open_l = db["open_lobbies"]
        retrieved_lobby = open_l.find_one({"lobby_id":self.lobby_id})
        active_l = db["active_lobbies"]
        for user in retrieved_lobby["users"]:
            user_info = {"lobby_id":self.lobby_id,
                         "user_id":user["user_id"],
                         "name":user["name"],
                         "likes":[]}
            active_l.insert_one(user_info)
        open_l.delete_one({"lobby_id":self.lobby_id})

    def add_like(self,place_id):
        if not self.is_in_lobby(): return False
        db = client["mydatabase"]
        active_l = db["active_lobbies"]
        retrieved_player = active_l.find_one({"user_id":self.user_id})
        if retrieved_player is None: return False
        active_l.update_one({"user_id":self.user_id},
                            {"$addToSet":{"likes":place_id}})
        return True

    def check_match(self):
        if not self.is_in_lobby(): return False
        db = client["mydatabase"]
        active_l = db["active_lobbies"]
        players = active_l.find({"lobby_id":self.lobby_id})
        if players is None: return False
        common = players[0]["likes"]
        for player in players:
            common = [c for c in common if c in player["likes"]]
        return len(common)>0
            


host = User("Cool guy")
id = host.create_lobby()
user = User("Other guy")
user.join_lobby(id)
host.start_lobby()
user.add_like(4402590845)
user.check_match()
host.add_like(4402590845)
host.check_match()

