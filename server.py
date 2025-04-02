import os
from livekit import api
from flask import Flask, request
from dotenv import load_dotenv
from flask_cors import CORS
from livekit.api import LiveKitAPI, ListRoomsRequest
import uuid
from livekit.api import DeleteRoomRequest
 
load_dotenv(dotenv_path=".env.local")
 
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
 
async def generate_room_name():
    name = "room-" + str(uuid.uuid4())[:8]
    rooms = await get_rooms()
    while name in rooms:
        name = "room-" + str(uuid.uuid4())[:8]
    return name
 
async def get_rooms():
    api = LiveKitAPI()
    rooms = await api.room.list_rooms(ListRoomsRequest())
    # await api.aclose()
    for room in rooms.rooms:
        await api.room.delete_room(DeleteRoomRequest(room = room.name))
    return [room.name for room in rooms.rooms]
 
@app.route("/getToken")
async def get_token():
    # name = request.args.get("name", "my name")
    # room = request.args.get("room", None)
    name = "chirag"
    # room = None
    # if not room:
    room = await generate_room_name()
       
    token = api.AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET")) \
        .with_identity(name)\
        .with_name(name)\
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room
        ))
   
    return token.to_jwt()
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

# m livekit import api
# from flask import Flask, request, jsonify
# from dotenv import load_dotenv
# from flask_cors import CORS
# from livekit.api import LiveKitAPI, ListRoomsRequest
# import uuid
# import redis
# import os
# import asyncio
 
# load_dotenv(dotenv_path=".env.local")
 
# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}})
 
# async def generate_room_name():
#     name = "room-" + str(uuid.uuid4())[:8]
#     rooms = await get_rooms()
#     while name in rooms:
#         name = "room-" + str(uuid.uuid4())[:8]
#     return name
 
# async def get_rooms():
#     api = LiveKitAPI()
#     rooms = await api.room.list_rooms(ListRoomsRequest())
#     await api.aclose()
#     return [room.name for room in rooms.rooms]
 
 
# redis_client = redis.StrictRedis(
#     # host='your-redis-name.redis.cache.windows.net',
#     host='RedisLivekit.redis.cache.windows.net',
#     port=6380,
#     password='zpir55fUl0BFP6cBXykbyWqfHN1ZBj22AAzCaF6YHSQ=',
#     ssl=True,
#     decode_responses=True,
#     db=0
# )
# print(redis_client.ping())
# print("Redis Connection Successful!")
 
# #
 
# stt_tasks = {}
 
 
# async def generate_room_name():
#     """Generate a unique room name."""
#     name = "room-" + str(uuid.uuid4())[:8]
#     rooms = await get_rooms()
#     while name in rooms:
#         name = "room-" + str(uuid.uuid4())[:8]
#     return name
 
 
# async def get_rooms():
#     """Fetch the list of existing rooms."""
#     async with LiveKitAPI() as api:
#         rooms = await api.room.list_rooms(ListRoomsRequest())
#         return [room.name for room in rooms.rooms]
 
 
# async def start_stt(room_name):
#     """Simulate STT service streaming."""
#     print(f"Starting STT for {room_name}...")
 
#     try:
#         for i in range(10):  # Simulating STT stream
#             print(f"STT streaming... {i}")
#             await asyncio.sleep(1)
#     except asyncio.CancelledError:
#         print("STT forcefully stopped!")
#     finally:
#         print("STT cleanup completed!")
 
 
# @app.route('/startSTT', methods=['POST'])
# async def start_stt_endpoint():
#     """Start STT service."""
#     data = request.get_json()
#     room_name = data.get("room_name", await generate_room_name())
 
#     # Store the STT task
#     if room_name in stt_tasks:
#         return jsonify({"error": "STT already running"}), 400
 
#     task = asyncio.create_task(start_stt(room_name))
#     stt_tasks[room_name] = task
 
#     return jsonify({"message": "STT started", "room": room_name})
 
 
# @app.route('/stopSTT', methods=['POST'])
# async def stop_stt():
#     """Forcefully stop STT service."""
#     data = request.get_json()
#     room_name = data.get("room_name")
 
#     if not room_name or room_name not in stt_tasks:
#         return jsonify({"error": "STT not running for this room"}), 404
 
#     # Cancel the STT task
#     task = stt_tasks.pop(room_name)
#     task.cancel()
 
#     try:
#         await task
#     except asyncio.CancelledError:
#         print(f"STT for {room_name} forcefully stopped!")
 
#     return jsonify({"message": "STT stopped", "room": room_name})
 
 
# #
 
# @app.route('/sendData', methods=['POST'])
# def receive_data():
#     data = request.get_json()
   
#     if not data:
#         return jsonify({"error": "No data received"}), 400  # Ensure a valid response
   
#     value = data["text"]
#     redis_client.set("context", value)
#     # redis_client.publish("context", value)    
#     # Process data (Make sure this function doesn't exit without a return    statement)  
#     # Debugging line
#     return jsonify({"message": "Data received successfully"}), 200
 
 
# @app.route("/getToken")
# async def get_token():
   
#     # name = request.args.get("name", "my name")
#     # room = request.args.get("room", None)
#     name = "chirag"
#     # room = None
#     # if not room:
#     room = await generate_room_name()
   
#     token = api.AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET")) \
#         .with_identity(name)\
#         .with_name(name)\
#         .with_grants(api.VideoGrants(
#             room_join=True,
#             room=room
#         ))
   
#     return token.to_jwt()
 
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5001, debug=True)