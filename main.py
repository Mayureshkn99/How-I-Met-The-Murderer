"""An App to automate the role selection process for the game Killer-Killer"""

from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
import socket
import threading
import random


Window.size = (350, 650)
Window.softinput_mode = "below_target"
HEADER = 64
FORMAT = 'utf-8'
DISCONNECT = "DISCONNECT"
STOP = False
PLAYERS = []
ROLES = ["Chor", "Police"]


class MyButton(MDFillRoundFlatButton):
    """Custom Definition of Button"""
    pass


class MyBoxLayout(MDBoxLayout):
    """Custom Definition of BoxLayout"""
    pass

class Player():

    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr


class HomePage(MDScreen):
    pass


class HostPage(MDScreen):

    def host(self):
        if self.ids.host_name.text == "":
            toast("Username cannot be blank")
        else:
            self.manager.current = "LobbyPage"
            self.manager.transition.direction = "left"


class LobbyPage(MDScreen):

    def on_enter(self):
        self.host_name = self.manager.get_screen("HostPage").ids.host_name.text
        self.ids.lobby_name.text = self.host_name + "'s Lobby"
        # self.host()

    def broadcast(self):
        global STOP

        # Initializing broadcast socket
        print("Started Broadcast")
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Broadcast IP address and Username Continuously
        message = (socket.gethostbyname(socket.getfqdn()) + ' ' + self.host_name).encode('utf-8')
        while True:
            broadcast_socket.sendto(message, ('<broadcast>', 8888))
            if STOP:
                broadcast_socket.close()
                print("Stopped Broadcast")
                STOP = False
                return

    def host(self):
        # Broadcast server IP
        threading.Thread(target=self.broadcast).start()

        # Initializing server object with ip '' and port 9999
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(None)
        server.bind(('', 9999))

        # Server listens for client connections
        server.listen()
        print("Listening...")
        while True:
            conn, addr = server.accept()
            if addr[0] == socket.gethostbyname(socket.gethostname()):
                conn.close()
                break  # Stop listening if received own addr
            conn.settimeout(None)
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            print("Active Connections: ", threading.activeCount() - 2)
        server.close()

    def handle_client(self, conn, addr):
        global PLAYERS, HEADER, FORMAT
        player = Player(conn, addr)
        print(addr, "connected")
        label = False
        while True:
            try:
                msg_length = conn.recv(HEADER).decode(FORMAT)
            except:
                msg_length = 0
                print("Connection Aborted 1")
            if msg_length:
                msg_length = int(msg_length)
                try:
                    msg = conn.recv(msg_length).decode(FORMAT)
                except:
                    msg = DISCONNECT
                    print("Connection Aborted 2")
                if msg == DISCONNECT:
                    if label:
                        PLAYERS.remove(next(x for x in PLAYERS if x.addr == addr))
                        self.ids.players_connected.remove_widget(label)
                        del self.ids[player.username]
                    conn.close()
                    break
                print("<", addr, ">", msg)
                player.username = msg
                label = MDLabel(text=player.username, halign="center")
                self.ids[player.username] = label
                self.ids.players_connected.add_widget(label)
                PLAYERS.append(player)

    def disconnect(self):
        global PLAYERS, STOP

        # Disconnect clients
        for player in PLAYERS:
            player.conn.close()
        PLAYERS = []

        STOP = True  # Stops Broadcast

        # Stops server listen
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client.settimeout(None)
        addr = socket.gethostbyname(socket.gethostname())
        client.connect((addr, 9999))
        client.close()

    def assign_roles(self):
        global PLAYERS, ROLES, STOP
        no_of_players = len(PLAYERS)
        if no_of_players < 3:
            toast("Cannot play with less than 3 Players")
            return
        roles = ROLES + ["Citizen"]*(len(PLAYERS)-1)
        self.role = random.choice(roles)
        roles.remove(self.role)
        random.shuffle(PLAYERS)
        for player, role in zip(PLAYERS, roles):
            role = role.encode(FORMAT)
            player.send(role)

        self.disconnect()

        self.manager.current = "RolePage"
        self.manager.transition.direction = "left"


class JoinPage(MDScreen):

    def connect_host(self, name):
        if self.ids.name.text == "":
            toast("Username cannot be blank")
            return
        self.dialog = MDDialog(
            text="Connect to "+name+"'s Lobby?",
            buttons=[
                MDFlatButton(text="Yes", on_release=self.connect),
                MDFlatButton(text="No", on_release=self.close_confirm)
            ]
        )
        self.dialog.open()

    def connect(self, _):
        self.dialog.dismiss()
        self.manager.get_screen("RolePage").ids.role.text = "Waiting for host to assign role..."
        self.manager.current = "RolePage"
        self.manager.transition.direction = "left"

    def close_confirm(self, _):
        self.dialog.dismiss()


class RolePage(MDScreen):

    def on_enter(self):
        self.ids.role.text = self.role


class WindowManager(ScreenManager):

    def __init__(self, **kwargs):
        super(WindowManager, self).__init__(**kwargs)
        Window.bind(on_keyboard=self.on_key)

    def on_key(self, window, key, *args):
        """Maps Screens to return to on back press"""

        if key == 27:  # the esc key
            if self.current_screen.name == "HomePage":
                return False  # exit the app from this page
            elif self.current_screen.name == "HostPage":
                self.current = "HomePage"
                self.transition.direction = "right"
                return True  # do not exit the app
            elif self.current_screen.name == "LobbyPage":
                # LobbyPage().disconnect()
                self.current = "HostPage"
                self.transition.direction = "right"
                return True  # do not exit the app
            elif self.current_screen.name == "RolePage":
                self.current = "HostPage"
                self.transition.direction = "right"
                return True  # do not exit the app
            elif self.current_screen.name == "JoinPage":
                self.current = "HomePage"
                self.transition.direction = "right"
                return True  # do not exit the app



class HIMTMApp(MDApp):

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        return None



if __name__ == "__main__":
    HIMTMApp().run()