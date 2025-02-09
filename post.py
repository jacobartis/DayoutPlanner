import requests
import datetime

url = "http://127.0.0.1:8000/lobbies/create"
#Shows example create post.
data = {
    "host_id":"TEST",
    "location":"Test",
    "preferences":{},
    "created_at":str(datetime.datetime.now()),
}
response = requests.post(url, json=data)
print(response.json()) 