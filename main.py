from database_manager.meta import db, EmptyUser, ENGINE, EmptyChat, EmptyMessage
from communication import *
from config import Config
import time


# define defaults
Running = True
CONNECTION = ENGINE.connect()
# create_table()
# exit()


def user_by_name(username: str, connection):
    query = db.select([EmptyUser]).where(EmptyUser.columns.username == username)
    result = connection.execute(query).fetchall()

    # no results
    if not result:
        raise KeyError(f"No user with name {username}")

    return result[0]


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

        try:
            match message["type"].lower():
                case "login":
                    username = message["username"].lower()
                    password = message["password"]

                    if len(password) != 512:
                        client.n_send({
                            "success": False,
                            "cause": "PwdNotHashed",
                            "details": "please hash the password before sending!"
                        })
                        continue

                    try:
                        user = user_by_name(username, sql_connection)

                    except KeyError:
                        client.n_send({
                            "success": False,
                            "cause": "UserDoesntExist",
                            "details": "The user you are currently trying to login to doesn't exist!"
                        })
                        continue

                    if user.password == password:
                        current_user = user
                        client.n_send({
                            "success": True,
                        })
                        break

                    client.n_send({
                        "success": False,
                        "cause": "WrongPassword",
                        "details": "You entered the wrong password for this account!"
                    })
                    continue

                case "register":
                    username = message["username"].lower()
                    password = message["password"]

                    if len(password) != 512:
                        client.n_send({
                            "success": False,
                            "cause": "PwdNotHashed",
                            "details": "please hash the password before sending!"
                        })
                        continue

                    # test if the user already exists
                    try:
                        user_by_name(username, sql_connection)
                        client.n_send({
                            "success": False,
                            "cause": "UsernameTaken",
                            "details": "An account with this username already exists. Please choose another one!"
                        })
                        continue

                    except KeyError:
                        # if not, add user to database
                        query = db.insert(EmptyUser).values(
                            username=username,
                            password=password,
                        )
                        sql_connection.execute(query)
                        client.n_send({
                            "success": True,
                        })
                        continue

                case _:
                    # user not logged in
                    client.n_send({
                        "success": False,
                        "cause": "NotLoggedIn",
                        "details": "You tried to use a function for which you need to be logged in!"
                    })
                    continue

        except KeyError:
            client.n_send({
                "success": False,
                "cause": "KeyError",
                "details": "Not all keys were specified!"
            })
            continue

    # check if the user has actually logged in
    if current_user is ...:
        client.socket.close()
        return

    # main loop
    while Running:
        try:
            message = client.n_recv()

        except (TimeoutError, OSError):
            continue

        try:
            match message["type"].lower():
                case "get_user":
                    search_for = message["keyword"] if "keyword" in message else ""
                    query = db.select([EmptyUser])
                    result = sql_connection.execute(query).fetchall()

                    out = []
                    for user in result:
                        if search_for in user[0]:
                            out.append(user[0])

                    client.n_send({
                        "success": True,
                        "data": out,
                    })

                case "get_chats":
                    query = db.select([EmptyChat])
                    result = sql_connection.execute(query).fetchall()

                    out: list[dict] = []
                    for chat in result:
                        if current_user.username in chat.users:
                            out.append({
                                "name": chat.name,
                                "id": chat.id,
                            })

                    client.n_send({
                        "success": True,
                        "data": out,
                    })

                case "send_message":
                    content = message["content"]
                    chat_id = message["chat_id"]

                    query = db.insert(EmptyMessage).values(
                        chat_id=chat_id,
                        content=content,
                        sent_from=current_user.username,
                        time_sent=time.time(),
                    )
                    sql_connection.execute(query)
                    client.n_send({
                        "success": True,
                    })

                case "get_messages":
                    chat_id = message["chat_id"]
                    query = db.select([EmptyMessage]).where(EmptyMessage.columns.chat_id == chat_id)
                    messages = sql_connection.execute(query).fetchall()

                    out: list[dict] = [dict(message) for message in messages]

                    print(messages)
                    client.n_send({
                        "success": True,
                        "data": out,
                    })

                case _:
                    client.n_send({
                        "success": False,
                        "cause": "MessageTypeNotKnown",
                        "details": f"the requested message type [{message['type']}] is not known!"
                    })
                    client.socket.close()
                    raise NotImplementedError(f"Unregistered  message type {message['type']}")

        except KeyError:
            client.n_send({
                "success": False,
                "cause": "KeyError",
                "details": "Not all keys were specified!"
            })
            continue


if __name__ == '__main__':
    Server = NSocketServer(Config.settings.server.port, client_handler)
    try:
        input("press enter to stop server ")

    finally:
        Running = False
        Server.end()
