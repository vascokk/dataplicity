from __future__ import print_function

from dataplicity.client.task import Task, onsignal


class KeyboardTask(Task):

    @onsignal('keyboard.key_down', 'keyboard1')
    def on_key_down(self, keyboard, key):
        pass

    @onsignal('keyboard.key_up', 'keyboard1')
    def on_key_up(self, keyboard, key):
        pass

    @onsignal('buttons.button_down', 'group1')
    def on_button_down(self, buttons, button):
        print("[{}] DOWN".format(button))

    @onsignal('buttons.button_up', 'group1')
    def on_button_up(self, buttons, button):
        print("[{}] UP".format(button))
