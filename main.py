from database_manager.meta import db, EmptyUser, ENGINE, EmptyChat, EmptyMessage  # , create_table
from sqlalchemy import update, delete
from communication import *
from hashlib import sha256
from config import Config
import typing as tp
import base64
import json
import time


# define defaults
Running = True
CONNECTION = ENGINE.connect()
# create_table()
# exit()


def handle_request(request_data: dict, current_user, sql_connection) -> dict:
    # default value
    # print(f"received request:\n{json.dumps(request_data, indent=4)}")
    out: dict[str, dict | tp.Any] = {
        "data": None,
        "current_user": current_user,
    }

    if ("late_hash" in request_data) and (request_data["late_hash"]) and ("password" in request_data):
        request_data["password"] = sha256(request_data["password"].encode()).hexdigest()

    try:
        if current_user is ...:
            match request_data["type"].lower():
                case "login":
                    username = request_data["username"]
                    password = request_data["password"]

                    if len(password) != 64:
                        out["data"] = {
                            "success": False,
                            "cause": "PwdNotHashed",
                            "details": "please hash the password before sending!"
                        }
                        return out

                    query = db.select([EmptyUser]).where(EmptyUser.columns.username == username)
                    result = sql_connection.execute(query).fetchall()

                    # no results
                    if not result:
                        out["data"] = {
                            "success": False,
                            "cause": "UserDoesntExist",
                            "details": "The user you are currently trying to login to doesn't exist!"
                        }
                        return out

                    user = result[0]

                    if user.password == password:
                        out["current_user"] = user
                        out["data"] = {
                            "success": True,
                        }
                        return out

                    out["data"] = {
                        "success": False,
                        "cause": "WrongPassword",
                        "details": "You entered the wrong password for this account!"
                    }

                    return out

                case "register":
                    username = request_data["username"]
                    password = request_data["password"]

                    if len(password) != 64:
                        out["data"] = {
                            "success": False,
                            "cause": "PwdNotHashed",
                            "details": "please hash the password before sending!"
                        }
                        return out

                    # test if the user already exists
                    query = db.select([EmptyUser]).where(EmptyUser.columns.username == username)
                    result = sql_connection.execute(query).fetchall()

                    if result:
                        out["data"] = {
                            "success": False,
                            "cause": "UsernameTaken",
                            "details": "An account with this username already exists. Please choose another one!"
                        }
                        return out

                    # if not, add user to database
                    query = db.insert(EmptyUser).values(
                        username=username,
                        password=password,
                    )
                    sql_connection.execute(query)
                    out["data"] = {
                        "success": True,
                    }
                    return out

                case _:
                    # user not logged in
                    out["data"] = {
                        "success": False,
                        "cause": "NotLoggedIn",
                        "details": "You tried to use a function for which you need to be logged in!"
                    }
                    return out

        else:
            try:
                match request_data["type"].lower():
                    case "login":
                        username = request_data["username"]
                        password = request_data["password"]

                        if len(password) != 64:
                            out["data"] = {
                                "success": False,
                                "cause": "PwdNotHashed",
                                "details": "please hash the password before sending!"
                            }
                            return out

                        query = db.select([EmptyUser]).where(EmptyUser.columns.username == username)
                        result = sql_connection.execute(query).fetchall()

                        # no results
                        if not result:
                            out["data"] = {
                                "success": False,
                                "cause": "UserDoesntExist",
                                "details": "The user you are currently trying to login to doesn't exist!"
                            }
                            return out

                        user = result[0]

                        if user.password == password:
                            out["current_user"] = user
                            out["data"] = {
                                "success": True,
                            }
                            return out

                        out["data"] = {
                            "success": False,
                            "cause": "WrongPassword",
                            "details": "You entered the wrong password for this account!"
                        }

                        return out

                    case "create_chat":
                        name = request_data["name"]
                        user_ids = request_data["user_ids"]

                        user_ids.append(current_user.id)
                        user_ids = list(set(user_ids))

                        actual_ids: list[int] = []
                        actual_users: list[str] = []
                        for user_id in user_ids:
                            query = db.select([EmptyUser]).where(EmptyUser.columns.id == user_id)
                            result = sql_connection.execute(query).fetchall()

                            if result:
                                actual_users.append(result[0].username)
                                actual_ids.append(result[0].id)

                        if not (actual_users and actual_ids):
                            out["data"] = {
                                "success": False,
                                "cause": "InvalidUsernames",
                                "details": "None of the given users were valid",
                            }
                            return out

                        query = db.insert(EmptyChat).values(
                            name=name,
                            user_ids=actual_ids,
                            user_names=actual_users,
                        )
                        sql_connection.execute(query)

                        out["data"] = {
                            "success": True,
                        }
                        return out

                    case "get_chats":
                        query = db.select([EmptyChat])
                        result = sql_connection.execute(query).fetchall()

                        tmp: list[dict] = []
                        for chat in result:
                            if current_user.id in chat.user_ids:
                                tmp.append({
                                    "user_names": chat.user_names,
                                    "user_ids": chat.user_ids,
                                    "name": chat.name,
                                    "id": chat.id,
                                })

                        out["data"] = {
                            "success": True,
                            "data": tmp,
                        }
                        return out

                    case "send_message":
                        content = request_data["content"]
                        chat_id = request_data["chat_id"]

                        query = db.insert(EmptyMessage).values(
                            sent_from_id=current_user.id,
                            time_sent=time.time(),
                            chat_id=chat_id,
                            content=content,
                        )
                        sql_connection.execute(query)
                        out["data"] = {
                            "success": True,
                        }
                        return out

                    case "get_messages":
                        # get all messages from a specified chat
                        chat_id = request_data["chat_id"]
                        query = db.select([EmptyMessage]).where(EmptyMessage.columns.chat_id == chat_id)
                        messages = sql_connection.execute(query).fetchall()

                        # creat JSON type dict and sort items
                        tmp: list[dict] = [dict(message) for message in messages]
                        tmp = sorted(tmp, key=lambda x: x["time_sent"])

                        # add usernames to all items
                        for i in range(len(tmp)):
                            # try to get information on the user who sent the message
                            query = db.select([EmptyUser]).where(EmptyUser.columns.id == tmp[i]["sent_from_id"])
                            result = sql_connection.execute(query).fetchall()

                            # in case the user doesn't exist anymore, it has been deleted
                            username = str(result[0].username) if result else "deleted"

                            # append info to message
                            tmp[i]["sent_from"] = username

                        out["data"] = {
                            "success": True,
                            "data": tmp,
                        }
                        return out

                    case "user_lookup":
                        # get a users username and id from either of them
                        username = user_id = ...
                        if "username" in request_data:
                            username = request_data["username"]
                            query = db.select([EmptyUser]).where(EmptyUser.columns.username == username)
                            user = sql_connection.execute(query).fetchall()

                        elif "id" in request_data:
                            user_id = request_data["id"]
                            query = db.select([EmptyUser]).where(EmptyUser.columns.id == user_id)
                            user = sql_connection.execute(query).fetchall()

                        else:
                            out["data"] = {
                                "success": False,
                                "cause": "KeyError",
                                "details": "Not all keys were specified!",
                            }
                            return out

                        tmp_out = {
                            "success": True,
                            "data": {
                                "requested_user": (username if username is not ... else user_id) if username is not ... or user_id else None,
                                "exists": not not user,
                            },
                        }

                        if user:
                            tmp_out["data"]["username"] = str(user[0].username)
                            tmp_out["data"]["id"] = int(user[0].id)

                        out["data"] = tmp_out

                        return out

                    case "leave_chat":
                        # leave a chat
                        chat_id = request_data["chat_id"]
                        query = db.select([EmptyChat]).where(EmptyChat.columns.id == chat_id)
                        chats = sql_connection.execute(query).fetchall()

                        if not chats:
                            out["data"] = {
                                "success": False,
                                "cause": "ChatDoesntExist",
                                "details": "The chat you were trying to leave doesn't exist",
                            }
                            return out

                        chat = chats[0]

                        if current_user.id in chat.user_ids:
                            # chat.user_ids.remove(current_user.id)
                            new_user_ids = chat.user_ids
                            new_user_ids.remove(current_user.id)

                            new_user_names = chat.user_names
                            new_user_names.remove(current_user.username)

                            if len(new_user_ids) == 1:
                                stmt = (
                                    delete(EmptyChat).
                                    where(EmptyChat.columns.id == chat_id)
                                )

                            else:
                                stmt = (
                                    update(EmptyChat).
                                    where(EmptyChat.columns.id == chat_id).
                                    values(user_ids=new_user_ids, user_names=new_user_names)
                                )

                            ENGINE.execute(stmt)

                            out["data"] = {
                                "success": True,
                            }
                            return out

                        out["data"] = {
                            "success": False,
                            "cause": "NotInChat",
                            "details": "You are not currently enrolled in the chat you were trying to leave.",
                        }
                        return out

                    case _:
                        raise NotImplementedError(f"Unregistered  message type {request_data['type']}")

            except KeyError:
                out["data"] = {
                    "success": False,
                    "cause": "KeyError",
                    "details": "Not all keys were specified!"
                }
                return out

    except KeyError:
        out["data"] = {
            "success": False,
            "cause": "KeyError",
            "details": "Not all keys were specified!"
        }
        return out


def client_handler(client: NSockExisting, address: tuple):
    """
    handle incoming clients
    """
    global Running
    print(f"new client: {address}")

    sql_connection = ENGINE.connect()
    client.socket.settimeout(.2)
    current_user = ...

    # login loop
    while Running:
        try:
            message = client.n_recv()

        except (TimeoutError, OSError):
            continue

        if message is None:
            continue

        try:
            result = handle_request(message, current_user, sql_connection)
            current_user = result["current_user"]
            data = result["data"]
            client.n_send(data)

        except NotImplementedError:
            client.n_send({
                "success": False,
                "cause": "MessageTypeNotKnown",
                "details": f"the requested message type [{message['type']}] is not known!"
            })
            client.socket.close()
            raise


async def web_client_handler(ws):
    print("new client (ws)")
    sql_connection = ENGINE.connect()
    current_user = ...

    async for message in ws:
        try:
            message = json.loads(message)["data"]

        except json.JSONDecodeError:
            message = base64.b64decode(message)
            message = json.loads(message)["data"]

        try:
            result = handle_request(message, current_user, sql_connection)
            current_user = result["current_user"]
            data = result["data"]
            if message["type"] not in ("get_chats", "get_messages"):
                print(f"request: {json.dumps(message, indent=4)}")
                print(f"sending: {data}")
                print(f"sending: {json.dumps(data, indent=4)}")

            await ws_send(data, ws)

        except NotImplementedError:
            await ws_send({
                "success": False,
                "cause": "MessageTypeNotKnown",
                "details": f"the requested message type [{message['type']}] is not known!"
            }, ws)
            ws.close()
            raise


if __name__ == '__main__':
    Server = NSocketServer(Config.settings.server.port, client_handler)

    import asyncio
    import websockets


    async def main():
        async with websockets.serve(web_client_handler, port=Config.settings.server.web_port, host=""):
            await asyncio.Future()  # run forever

    try:
        asyncio.run(main())
        input("press enter to stop server ")

    finally:
        Running = False
        Server.end()
