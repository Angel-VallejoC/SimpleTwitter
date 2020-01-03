import socket
from time import time
from _thread import *


class SimpleTwitterServer:

    def __init__(self):
        # create socket for client-server connection
        self.SERVER_HOST = ''
        self.SERVER_PORT = 7143
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # create socket for sending new tweets
        self.TWEET_HOST = ''
        self.TWEET_PORT = 7145
        self.newtweet_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.newtweet_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.users = {"user1": "password1", "user2": "password2", "user3": "password3"}  # user:password
        self.connected_users = dict()  # user:connection
        self.offline_messages = dict()  # user:list of posts
        self.posts = []  # list of posts
        self.user_subscribers = dict()  # user:list of subscribers "followers
        self.user_subscriptions = dict()  # user: list of subscriptions

        
    def start(self):
        try:
            self.server_socket.bind((self.SERVER_HOST, self.SERVER_PORT))
            self.newtweet_socket.bind((self.TWEET_HOST, self.TWEET_PORT))
        except socket.error as msg:
            print("Bind failed. Message: ", msg)
        print("Socket bind complete.")

        self.server_socket.listen(10)
        self.newtweet_socket.listen(10)
        print(f"Socket now listening on port {self.SERVER_PORT}")
        self.run()

    def run(self):
        while True:
            connection, address = self.server_socket.accept()
            newtweet_connection, address2 = self.newtweet_socket.accept()
            print(f"Connected with {address[0]}:{address[1]}")
            print(f"Connected with {address2[0]}:{address2[1]} (newtweet socket)")

            start_new_thread(self.client_thread, (connection, newtweet_connection, address))

    def client_thread(self, connection, newtweet_con, address):
        user = ""
        request = connection.recv(1024)
        while request:

            print(request)
            parameters = request.decode("UTF-8").split('|')
            try:
                code = int(parameters[0])
            except ValueError:
                response = "400"
                connection.sendall(response.encode("UTF-8"))

            if code == 0:  # login
                user = self.manage_login(connection, newtweet_con, parameters)
            elif code == 1:  # show all offline messages
                self.show_offline_messages(connection, parameters, user)
            elif code == 2:  # show offline messages by subscription
                self.show_offline_bysub(connection, parameters, user)
            # elif code == 3:  # validate username
            elif code == 4:  # add subscription
                self.add_subscription(connection, parameters, user)
            elif code == 5:  # get subscriptions from user
                self.get_subscription(connection, user)
            elif code == 6:  # delete subscription
                self.delete_subscription(connection, parameters, user)
            elif code == 7:  # post message
                self.post_message(connection, newtweet_con, parameters, user)
            elif code == 10:  # logout
                self.logout(connection, parameters, user)
                break
            elif code == 11:    # get posts by hashtag
                self.search_hashtag(connection, parameters)

            request = connection.recv(1024)
        print(f"Connection with client {address[0]}:{address[1]} finished")
        connection.close()
        newtweet_con.close()

    def manage_login(self, connection, newtweet_con, parameters):
        user = parameters[1]
        password = parameters[2]
        if user in self.users and password == self.users[user]:
            total_offline = 0 if user not in self.offline_messages else len(self.offline_messages[user])
            response_message = f"200|Welcome to Simple Twitter! You have {total_offline} offline posts"
            # login succeeded, add to connected users
            self.connected_users[user] = (connection, newtweet_con)
            connection.sendall(response_message.encode("UTF-8"))
            return user

        response_message = "400|Authentication failed"
        connection.sendall(response_message.encode("UTF-8"))
        return ""

    def show_offline_messages(self, connection, parameters, user):
        if user in self.offline_messages:
            response_message = "200"
            for post in self.offline_messages[user]:
                response_message = f"{response_message}|{post['author']};{post['tweet']};{post['hashtag']}"
            self.offline_messages.pop(user)
        else:
            response_message = "204"

        connection.sendall(response_message.encode("UTF-8"))

    def show_offline_bysub(self, connection, parameters, user):
        if user in self.offline_messages:
            response_message = ""
            i = 0
            delete = []
            for post in self.offline_messages[user]:
                if post['author'] == parameters[1]:
                    response_message = f"{response_message}|{post['author']};{post['tweet']};{post['hashtag']}"
                    delete.append(i)
                i += 1

            deleted = 0
            for i in delete:
                self.offline_messages[user].pop(i - deleted)
                deleted += 1

            if len(self.offline_messages[user]) == 0:
                self.offline_messages.pop(user)

            if len(response_message) == 0:
                response_message = "204"
            else:
                response_message = "200" + response_message
        else:
            response_message = "204"

        connection.sendall(response_message.encode("UTF-8"))

    def add_subscription(self, connection, parameters, current_user):
        user = parameters[1]

        if user not in self.users:
            response = "204|User does not exist"
            connection.sendall(response.encode("UTF-8"))
            return

        if current_user not in self.user_subscriptions or len(self.user_subscriptions[current_user]) == 0:
            self.user_subscriptions[current_user] = {user}
        else:
            self.user_subscriptions[current_user].add(user)

        if user not in self.user_subscribers or len(self.user_subscribers[user]) == 0:
            self.user_subscribers[user] = {current_user}
        else:
            print(self.user_subscribers[user])
            self.user_subscribers[user].add(current_user)

        response = "200|Subscription created"
        connection.sendall(response.encode("UTF-8"))

    def delete_subscription(self, connection, parameters, current_user):
        user = parameters[1]
        if current_user in self.user_subscriptions:
            if user in self.user_subscriptions[current_user]:
                self.user_subscriptions[current_user].remove(user)
            else:
                response = "204"
                connection.sendall(response.encode("UTF-8"))
                return

        if user in self.user_subscribers:
            if current_user in self.user_subscribers[user]:
                self.user_subscribers[user].remove(current_user)

        response = "200"
        connection.sendall(response.encode("UTF-8"))

    def post_message(self, connection, newtweet_con, parameters, current_user):
        if len(parameters[1]) > 140:
            response_message = "400|Twit too long"
            connection.sendall(response_message.encode("UTF-8"))
            return

        # send to subscribers, if they are not connected store it as offline message
        if current_user in self.user_subscribers:  # send to current_user subscribers only
            for user in self.user_subscribers[current_user]:
                if user in self.connected_users:
                    send_message = f"201|{current_user};{parameters[1]};{parameters[2]}"
                    self.connected_users[user][1].sendall(send_message.encode("UTF-8"))
                else:
                    if user in self.offline_messages:
                        self.offline_messages[user].append(
                            {"author": current_user, "tweet": parameters[1], "hashtag": parameters[2]}
                        )
                    else:
                        self.offline_messages[user] = [
                            {"author": current_user, "tweet": parameters[1], "hashtag": parameters[2]}
                        ]

        # add post to posts list
        self.posts.append(
            {"author": current_user, "tweet": parameters[1], "hashtag": parameters[2]}
        )

        response_message = "200| Tweet was succesfully sent"
        connection.sendall(response_message.encode("UTF-8"))

    def get_subscription(self, connection, user):
        if user in self.user_subscriptions and len(self.user_subscriptions[user]) > 0:
            response = "200"
            for sub in self.user_subscriptions[user]:
                response = response + "|" + sub
            connection.sendall(response.encode("UTF-8"))
        else:
            response = "204"
            connection.sendall(response.encode("UTF-8"))

    def search_hashtag(self, connection, parameters):
        print("test")
        response = "200"
        count = 0
        last_posts = self.posts.copy()
        last_posts.reverse()
        for post in last_posts:
            if parameters[1] in post['hashtag']:
                response = f"{response}|{post['author']};{post['tweet']};{post['hashtag']}"
                count += 1

            if count == 10:
                break

        if len(response) == 3:
            response = "204"

        connection.sendall(response.encode("utf-8"))

    def logout(self, connection, parameters, user):
        if user in self.connected_users:
            self.connected_users.pop(user)
        connection.close()


server = SimpleTwitterServer()
server.start()
