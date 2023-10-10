"""An App to automate the role selection process for the game Killer-Killer"""

from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton, MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from functools import partial
from kivymd.toast import toast
from kivy.clock import mainthread, Clock
from kivy.logger import Logger, LOG_LEVELS
import socket
import threading
import random
import time


Window.size = (350, 650)
Window.softinput_mode = "below_target"
HEADER = 64
FORMAT = 'utf-8'
DISCONNECT = "DISCONNECT"
STOP = False
PLAYERS = []
ROLES = ["Chor", "Police"]
Logger.setLevel(LOG_LEVELS["debug"])


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


class Host():

    def __init__(self, ip, name):
        self.ip = ip
        self.name = name


class HomePage(MDScreen):
    pass


class HostPage(MDScreen):

    def host(self):
        if self.ids.host_name.text == "":
            Logger.warning("HostPage: Username is blank")
            toast("Username cannot be blank")
        else:
            self.manager.current = "LobbyPage"
            self.manager.transition.direction = "left"


class LobbyPage(MDScreen):

    def on_enter(self):
        self.host_name = self.manager.get_screen("HostPage").ids.host_name.text
        self.ids.lobby_name.text = self.host_name + "'s Lobby"
        self.host()

    def broadcast(self):
        global STOP

        # Initializing broadcast socket
        Logger.info("LobbyPage: Broadcast Started")
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_socket.settimeout(None)


        # Broadcast IP address and Username Continuously
        message = (socket.gethostbyname(socket.getfqdn()) + ' ' + self.host_name).encode('utf-8')
        Logger.debug(f"LobbyPage: Broadcast Message <{message}>")
        while True:
            broadcast_socket.sendto(message, ('<broadcast>', 8888))
            time.sleep(1)
            if STOP:
                msg = (socket.gethostbyname(socket.getfqdn()) + ' ' + self.host_name + ' ' + DISCONNECT).encode('utf-8')
                broadcast_socket.sendto(msg, ('<broadcast>', 8888))
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

        # Start listening to client connection requests
        threading.Thread(target=self.listen, args=(server, )).start()

    def listen(self, server):
        # Server listens for client connections
        server.listen()
        Logger.info(f"LobbyPage: Listening for incomming connection requests")
        
        while True:
            conn, addr = server.accept()
            Logger.debug(f"LobbyPage: Accepted - {conn} | {addr}")
            # if addr[0] == socket.gethostbyname(socket.gethostname()):
            #     conn.close()
            #     break  # Stop listening if received own addr
            conn.settimeout(None)
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()
            Logger.debug(f"LobbyPage: Active Connections - {threading.activeCount() - 2}")
        server.close()
        print("Server closed")

    def handle_client(self, conn, addr):
        global PLAYERS, HEADER, FORMAT
        player = Player(conn, addr)
        Logger.info(f"LobbyPage: {addr} connected")
        label = False
        while True:
            try:
                msg_length = conn.recv(HEADER).decode(FORMAT)
            except:
                print("Connection Aborted 1")
                break
            if msg_length:
                msg_length = int(msg_length)
                try:
                    msg = conn.recv(msg_length).decode(FORMAT)
                except:
                    print("Connection Aborted 2")
                    break
                if msg == DISCONNECT:
                    if label:
                        PLAYERS.remove(next(x for x in PLAYERS if x.addr == addr))
                        self.ids.players_connected.remove_widget(label)
                        del self.ids[player.username]
                    conn.close()
                    break
                player.username = msg
                threading.Thread(target=self.add_players, args=(player, )).start()
                PLAYERS.append(player)
    
    @mainthread
    def add_players(self, player):
        Logger.debug(f"LobbyPage: Adding player - {player.username}")
        label = MDLabel(text=player.username, halign="center")
        self.ids[player.username] = label
        self.ids.players_connected.add_widget(label)

    def disconnect(self):
        global PLAYERS, STOP

        # Disconnect clients
        for player in PLAYERS:
            player.conn.send(DISCONNECT)
            player.conn.close()
            self.ids.players_connected.remove_widget(player.username)
            del self.ids[player.username]
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
        if no_of_players < 1:
            toast("Cannot play with less than 3 Players")
            return
        roles = ROLES + ["Citizen"]*(len(PLAYERS)-1)
        Screen = self.manager.get_screen("RolePage")
        role = random.choice(roles)
        Screen.ids.role.text = role
        roles.remove(role)
        random.shuffle(PLAYERS)
        for player, role in zip(PLAYERS, roles):
            role = role.encode(FORMAT)
            Logger.debug(f"LobbyPage: Sending role - {player.username} | {role}")
            player.conn.send(role)
            Logger.debug(f"LobbyPage: Role sent")

        # self.disconnect()

        self.manager.current = "RolePage"
        self.manager.transition.direction = "left"


class JoinPage(MDScreen):

    def on_enter(self):
        threading.Thread(target=self.discover_host).start()
        self.host_ips = []
        self.hosts = []
        self.dialog = None

    def discover_host(self):
        Logger.info("JoinPage: Discovering Hosts")
        self.broadcastSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcastSocket.settimeout(None)
        self.broadcastSocket.bind(('', 8888))
        while True:
            host = self.broadcastSocket.recv(1024).decode(FORMAT)
            host = host.split()
            Logger.debug(f"JoinPage: Discovered Host - {host}")
            # Disconnect message from host
            if len(host) > 2:
                ip = host[0]
                host = next(x for x in self.hosts if x.ip == ip)
                self.ids.hosts.remove_widget(self.ids[host.name])
                del self.ids[host.name]
                self.hosts.remove(host)
                self.host_ips.remove(ip)
                continue
            ip, name = host
            if ip not in self.host_ips:
                self.host_ips.append(ip)
                threading.Thread(target=self.create_button, args= (ip, name)).start()
    
    @mainthread
    def create_button(self, ip, name):
        Logger.debug("JoinPage: Creating button")
        host = Host(ip, name)
        button = MDRaisedButton(text=name, size_hint_x=0.8,
                                on_release=partial(self.connect_host, ip, name))
        host.button = button
        self.hosts.append(host)
        self.ids.hosts.add_widget(button)
        Logger.debug(f"JoinPage: Added - {ip} | {name}")
        self.ids[name] = button


    def connect_host(self, ip, name, _):
        if self.ids.name.text == "":
            Logger.warning("JoinPage: Username is blank")
            toast("Username cannot be blank")
            return
        self.dialog = MDDialog(
            text="Connect to "+name+"'s Lobby?",
            buttons=[
                MDFlatButton(text="Yes", on_release=partial(self.connect, ip)),
                MDFlatButton(text="No", on_release=self.close_confirm)
            ]
        )
        self.dialog.open()

    def connect(self, ip, _):
        self.dialog.dismiss()
        self.dialog = None

        # Connect to Host
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client.settimeout(None)
        Logger.info("JoinPage: Connecting to host")
        self.client.connect((ip, 9999))

        # Send Username
        username = self.ids.name.text.encode(FORMAT)
        msg_length = len(username)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        Logger.debug("JoinPage: Sending length")
        self.client.send(send_length)
        Logger.info("JoinPage: Sending username")
        self.client.send(username)

        Screen = self.manager.get_screen("RolePage")
        Screen.ids.role.text = "Waiting for host to assign role..."
        self.manager.current = "RolePage"
        self.manager.transition.direction = "left"

    def close_confirm(self, _):
        self.dialog.dismiss()

    def disconnect(self):
        Screen = self.manager.get_screen("RolePage")
        self.broadcastSocket.close()
        for host in self.hosts:
            self.ids.hosts.remove_widget(self.ids[host.name])
            del self.ids[host.name]
        self.host_ips = self.hosts = []
        Screen.ids.role.text = "Not Assigned"
        self.client.close()

class RolePage(MDScreen):

    def on_enter(self):
        if self.ids.role.text == "Waiting for host to assign role...":
            Screen = self.manager.get_screen("JoinPage")
            try:
                Logger.info("RolePage: Ready to receive role")
                role = Screen.client.recv(1024).decode(FORMAT)
                Logger.debug(f"RolePage: Role received - {role}")
                if role == DISCONNECT:
                    Screen.disconnect()
                    self.manager.current = "JoinPage"
                    self.manager.transition.direction = "right"
                    return
                self.ids.role.text = role
                # Screen.disconnect()
            except:
                return





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
                LobbyPage().disconnect()
                self.current = "HostPage"
                self.transition.direction = "right"
                return True  # do not exit the app
            elif self.current_screen.name == "RolePage":
                self.current = "HomePage"
                self.transition.direction = "right"
                return True  # do not exit the app
            elif self.current_screen.name == "JoinPage":
                JoinPage().disconnect()
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