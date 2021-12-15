"""An App to automate the role selection process for the game Killer-Killer"""

from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast

Window.size = (350, 650)
Window.softinput_mode = "below_target"
HEADER = 64
FORMAT = 'utf-8'
DISCONNECT = "DISCONNECT"
PLAYERS = []
ROLES = ["Chor", "Police"]


class MyButton(MDFillRoundFlatButton):
    """Custom Definition of Button"""
    pass


class MyBoxLayout(MDBoxLayout):
    """Custom Definition of BoxLayout"""
    pass


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


class JoinPage(MDScreen):

    def connect_host(self,name):
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
    pass


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