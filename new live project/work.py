from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = b'_5#y2L"F4Q8z\n\xec]/'  # Change the secret key to a random value for encryption
socketio = SocketIO(app)

rooms = {}
private_chats = {}  # Add a dictionary to track private chats between users


def generate_unique_code(length):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            return code


def get_room_data():
    room = session.get("room")
    name = session.get("name")
    return room, name


@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        is_public = request.form.get("public", False) == "true"

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create:
            room = generate_unique_code(4)
            rooms[room] = {"creator": name, "members": [name], "messages": [], "public": is_public}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    # Pass the list of public rooms to the template
    public_room_list = [{"code": code, "creator": rooms[code]["creator"]} for code in rooms if rooms[code]["public"]]
    return render_template("home.html", public_room_list=public_room_list)


@app.route("/room")
def room():
    room, name = get_room_data()
    if not room or not name or room not in rooms:
        return redirect(url_for("home"))

    # Fetch the list of members in the room
    members = [member for member in rooms[room]["members"] if member != name]

    # Fetch private messages for the current user
    private_messages = private_chats.get(name, {}).get("messages", [])

    return render_template("room.html", code=room, messages=rooms[room]["messages"], members=members, private_messages=private_messages)


@socketio.on("message")
def message(data):
    room, name = get_room_data()
    if room not in rooms:
        return

    content = {
        "name": name,
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{name} said: {data['data']}")


@socketio.on("connect")
def connect():
    room, name = get_room_data()
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"].append(name)
    print(f"{name} joined room {room}")


@socketio.on("disconnect")
def disconnect():
    room, name = get_room_data()
    if room in rooms:
        rooms[room]["members"].remove(name)
        if len(rooms[room]["members"]) <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")


if __name__ == "__main__":
    socketio.run(app, debug=True, use_reloader=False)
