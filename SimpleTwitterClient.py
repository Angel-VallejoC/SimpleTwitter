import socket
import sys
from _thread import start_new_thread
import threading


class SimpleTwitterClient:

    def __init__(self):

        self.host = "localhost"
        self.port = 7143
        self.newtweet_port = 7145
        self.running = True

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.newtweet_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as msg:
            print('Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1])
            sys.exit()
        print("Socket created")

        self.client_socket.connect((self.host, self.port))
        self.newtweet_socket.connect((self.host, self.newtweet_port))
        self.newtweet_socket.setblocking(0)
        self.newtweet_socket.settimeout(15)

        print("Client connected")
        self.login()

    def listen_new_tweets(self):

        while True:
            try:
                request = self.newtweet_socket.recv(4096).decode("UTF-8").split("|")
                print(f"\nNew post!")
                if request[0] == "201":
                    for post in request[1:]:
                        self.print_post(post)
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    # print('recv timed out, retry later')
                    continue
                else:
                    print(e)
                    sys.exit(1)
            except socket.error as e:
                print(e)
                sys.exit(1)

            if not self.running:
                break

    def login(self):
        username = str(input("Username: "))
        password = str(input("Password: "))

        self.client_socket.send(f"0|{username}|{password}".encode("UTF-8"))

        response = self.client_socket.recv(1024).decode("UTF-8").split("|")

        if response[0] == "200":  # user logged in
            print(response[1])

            self.tweet_thread = threading.Thread(target=self.listen_new_tweets, args=())
            self.tweet_thread.daemon = True
            self.tweet_thread.start()
            #start_new_thread(self.listen_new_tweets, ())
            while True:
                self.show_menu()
        else:  # authentication failed
            print(response[1])

    def show_menu(self):
        print("\nWhat would you like to do?")
        print("1. See offline messages")
        print("2. Edit subscriptions")
        print("3. Post a message")
        print("4. Hashtag search")
        print("5. Logout")
        print("At any time you can enter -1 to go back to the menu\n")

        try:
            option = int(input())
        except ValueError:
            print("Invalid input.")
            return

        while option > 5 or option < 1:
            print("Enter a valid value")
            option = int(input())

        if option == 1:
            self.show_offline_messages()
        elif option == 2:
            self.edit_subscriptions()
        elif option == 3:
            self.post_message()
        elif option == 4:
            self.hashtag_search()
        elif option == 5:
            self.logout()

    def print_post(self, post):
        post = post.split(';')
        print("*********************************")
        print(post[1])
        print(post[2])
        print(f"By {post[0]}")
        print("*********************************")

    def show_offline_messages(self):
        choice = input("Do you want to show all messages or select by subscription? (ALL/SUB): ")

        if choice == "-1":
            return

        while not (choice.lower() == "all" or choice.lower() == "sub"):
            print("Enter a valid option")
            choice = input("Do you want to show all messages or select by subscription? (ALL/SUB): ")

        if choice.lower() == "all":
            # request all offline messages for the user
            request = f"1"
            self.client_socket.sendall(request.encode("UTF-8"))
            response = self.client_socket.recv(1024).decode("UTF-8").split("|")

            if response[0] == "200":
                print("Showing all offline messages")
                for post in response[1:]:
                    self.print_post(post)

            elif response[0] == "204":
                print("You have no offline messages")
        elif choice.lower() == "sub":
            request = "5"
            self.client_socket.sendall(request.encode("UTF-8"))
            response = self.client_socket.recv(4096).decode("UTF-8").split("|")

            if response[0] == "200":
                print("The following are your subscriptions. ")
                for user in response[1:]:
                    print(" - " + user)

                sub = input("Type in the user you want to see offline messages from: ")

                request = f"2|{sub}"
                self.client_socket.sendall(request.encode("UTF-8"))
                response = self.client_socket.recv(4096).decode("UTF-8").split("|")

                if response[0] == "200":
                    print(f"Showing offline messages from {sub}")
                    for post in response[1:]:
                        self.print_post(post)
                elif response[0] == "204":
                    print(f"You have no offline message from {sub}")

            elif response[0] == "204":
                print("You have no subscriptions to choose from")

    def edit_subscriptions(self):
        choice = input("Do you wish to add or delete a subscription? (add/delete): ")

        if choice == "-1":
            return

        while not (choice.lower() == "add" or choice.lower() == "delete"):
            print("Enter a valid option. ")
            choice = input("Do you wish to add or delete a subscription? (add/delete): ")

        if choice.lower() == "add":
            subscribe_to = input("Enter the username you want to subscribe to: ")

            request = f"4|{subscribe_to}"
            self.client_socket.sendall(request.encode("UTF-8"))
            response = self.client_socket.recv(4096).decode("UTF-8").split("|")

            if response[0] == "200":
                print(f"Subscribed to {subscribe_to} successfullly!")
            elif response[0] == "204":
                print(f"{subscribe_to} is not a valid username")
        else:
            request = "5"
            self.client_socket.sendall(request.encode("UTF-8"))
            response = self.client_socket.recv(4096).decode("UTF-8").split("|")

            if response[0] == "200":
                print("The following are your subscriptions. ")
                for user in response[1:]:
                    print(" - " + user)

                sub = input("Type in the user you want to unsubscribe from: ")
                request = f"6|{sub}"
                self.client_socket.sendall(request.encode("UTF-8"))
                response = self.client_socket.recv(4096).decode("UTF-8")

                if response == "200":
                    print(f"Your subscription to {sub} was succesfully deleted.")
                elif response == "204":
                    print(f"You are not subscribed to {sub}.")


            elif response[0] == "204":
                print("You have no subscriptions.")

    def post_message(self):
        tweet = input("Write your tweet: ")

        if tweet == "-1":
            return

        while len(tweet) > 140:
            print("The tweet must be 140 characters or less. Try again: ")
            tweet = input()

        hashtags = input("Enter the hashtags for the tweet: ")

        if hashtags == "-1":
            return

        request = f"7|{tweet}|{hashtags}"
        self.client_socket.sendall(request.encode("UTF-8"))

        response = self.client_socket.recv(4096).decode("UTF-8").split("|")

        if response[0] == "200":
            print("Your tweet was successfully sent")
        elif response[0] == "400":
            print("Your tweet must be at most 140 characters")

    def hashtag_search(self):
        search = input("Enter the hashtag you want to search: ")

        if search == "-1":
            return

        while len(search) == 0 or search[0] != "#":
            print("Wrong format (#yourhashtag). Try again.")
            search = input("Enter the hashtag you want to search: ")

        request = f"11|{search}"
        self.client_socket.sendall(request.encode("UTF-8"))
        response = self.client_socket.recv(4096).decode("UTF-8").split("|")

        if response[0] == "200":
            print(f"Results for {search}: ")
            for post in response[1:]:
                self.print_post(post)

        elif response[0] == "204":
            print(f"There were no results for {search}")

    def logout(self):
        request = "10"
        self.client_socket.sendall(request.encode("UTF-8"))
        print("Logged out successfully, thank you for using Simple Twitter.")
        self.running = False
        self.client_socket.close()
        self.newtweet_socket.close()
        self.tweet_thread.join()
        exit(0)


client = SimpleTwitterClient()
