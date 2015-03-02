import weakref


class ButtonGroup(object):
    def __init__(self, client, name):
        self._client = weakref.ref(client)
        self.name = name
        self.buttons = {}

    def add_button(self, name):
        button = Button(name)
        self.buttons[name] = button

    @property
    def client(self):
        return self._client()

    def pressed(self, name):
        pass


class Button(object):

    def __init__(self, name):
        self.name = name
