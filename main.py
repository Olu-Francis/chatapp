from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import random
from string import ascii_uppercase
from pymongo import MongoClient

app = Flask(__name__)
app.config["SECRET_KEY"] = 'secret!1233'
socketio = SocketIO(app)

# Connect to MongoDB
client = MongoClient("mongodb+srv://dansmatd123:Mongodbpass1.@cluster0.8snbx2x.mongodb.net/")
db = client["chat_database"]
rooms = db["rooms"]

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        # Check if the generated code already exists in the rooms collection
        if not rooms.find_one({"room_code": code}):
            break

    return code

@app.route('/', methods=["POST", "GET"])
def index():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template('index.html', error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template('index.html', error="Please enter a room code.", code=code, name=name)

        room = code

        if False != create:
            # Generate a unique room code
            room = generate_unique_code(4)
            # Insert a new document into the rooms collection
            rooms.insert_one({"room_code": room, "members": 0, "messages": []})
        elif not rooms.find_one({"room_code": code}):
            return render_template('index.html', error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template('index.html')

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or not rooms.find_one({"room_code": room}):
        return redirect(url_for("index"))

    room_data = rooms.find_one({"room_code": room})
    return render_template("room.html", code=room, messages=room_data['messages'])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if not rooms.find_one({"room_code": room}):
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    # Update the messages field of the room document
    rooms.update_one({"room_code": room}, {"$push": {"messages": content}})

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return

    if not rooms.find_one({"room_code": room}):
        leave_room(room)
        return

    join_room(room)
    alert = {"name": name, "message": "has joined"}
    send(alert, to=room)
    # Increment the members field of the room document
    rooms.update_one({"room_code": room}, {"$inc": {"members": 1}})
    # Update the messages field of the room document
    rooms.update_one({"room_code": room}, {"$push": {"messages": alert}})

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if rooms.find_one({"room_code": room}):
        # Decrement the members field of the room document
        rooms.update_one({"room_code": room}, {"$inc": {"members": -1}})
        room_data = rooms.find_one({"room_code": room})
        # if room_data["members"] < 1:
        #     # If there are no more members in the room, delete the room document
        #     rooms.delete_one({"room_code": room})

    alert = {"name": name, "message": "has left."}
    send(alert, to=room)
    # Update the messages field of the room document
    rooms.update_one({"room_code": room}, {"$push": {"messages": alert}})

if __name__ == "__main__":
    socketio.run(app, host="localhost", port=5000, debug=True, allow_unsafe_werkzeug=True)
