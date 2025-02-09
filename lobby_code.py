import pymongo
import datetime

mongo_data = open("mongo_data.txt").read()
# Replace with your MongoDB Atlas connection string
mongo_uri = f"mongodb+srv://{mongo_data}@cluster0.wd4xi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
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
        self.lobby_id = int(str(abs(hash(self.name.capitalize()+str(datetime.datetime.now()))))[:6])
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
        collection = db["open_lobbies"]
        collection.update_one({"lobby_id":self.lobby_id},
                              {"$pull":{"users":self.name}})
        if self.is_host:
            collection.delete_one({"lobby_id":self.lobby_id})
            self.is_host = False
        self.lobby_id = None
        return True

    def add_like(self,place_id):
        if not self.is_in_lobby(): return False
        db = client["mydatabase"]
        active_l = db["active_lobbies"]
        retrieved_player = active_l.find_one({"user_id":self.user_id})
        if retrieved_player is None: return False
        active_l.update_one({"user_id":self.user_id},
                            {"$addToSet":{"likes":place_id}})
        return True



class LobbyUtils:

    def get_matches(lobby_id:int):
        if not lobby_id: return []
        db = client["mydatabase"]
        active_l = db["active_lobbies"]
        users = active_l.find({"lobby_id":lobby_id})
        if users is None: return []
        common = users[0]["likes"]
        for user in users:
            common = [c for c in common if c in user["likes"]]
        return common
    
    def save_result(lobby_id:int):
        if not lobby_id: return False
        matches = LobbyUtils.get_matches(lobby_id)
        if len(matches)==0: return False
        db = client["mydatabase"]
        results = db["lobby_results"]
        lobby_res = results.find_one({"lobby_id":lobby_id})
        if lobby_res is None:
            results.insert_one({"lobby_id":lobby_id,
                                "results":[matches[0]]})
            print("New")
        else:
            results.update_one({"lobby_id":lobby_id},
                               {"$push":{"results":matches[0]}})
            print("Old")
        return True
        

    def new_round(lobby_id:int):
        if not lobby_id: return False
        db = client["mydatabase"]
        active_l = db["active_lobbies"]
        users = active_l.find({"lobby_id":lobby_id})
        if users is None: return False
        for user in users:
            active_l.update_one({"user_id":user["user_id"]},
                                {"$set":{"likes":[]}})
    
    def start_lobby(lobby_id:int):
        db = client["mydatabase"]
        open_l = db["open_lobbies"]
        retrieved_lobby = open_l.find_one({"lobby_id":lobby_id})
        active_l = db["active_lobbies"]
        if retrieved_lobby is None: return False
        for user in retrieved_lobby["users"]:
            user_info = {"lobby_id":lobby_id,
                         "user_id":user["user_id"],
                         "name":user["name"],
                         "likes":[]}
            active_l.insert_one(user_info)
        open_l.delete_one({"lobby_id":lobby_id})



# host = User("Cool guy")
# id = host.create_lobby()
# user = User("Other guy")  
# user.join_lobby(id)
# LobbyUtils.start_lobby(id) 
# user.add_like(4402590845)
# print(LobbyUtils.get_matches(id))
# host.add_like(4402590845)
# print(LobbyUtils.get_matches(id))
# print(LobbyUtils.save_result(id))
# print(LobbyUtils.save_result(id))
# print(LobbyUtils.save_result(id))

# host = User("Cool gsfdgsuy")
# id = host.create_lobby()
# user = User("Other fdsgguy")  
# user.join_lobby(id)

# host = User("Cool gusey")
# id = host.create_lobby()
# user = User("Other gfdsgdguy")  
# LobbyUtils.join_lobby(id)
# host.start_lobby()