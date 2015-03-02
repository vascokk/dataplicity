from __future__ import print_function

from dataplicity.client.task import Task, onsignal


class KeyboardTask(Task):

    @onsignal('keyboard.key_down', 'keyboard1')
    def on_key_down(self, keyboard, key):
        print(keyboard, key)
        pass

    @onsignal('keyboard.key_down', 'keyboard1')
    def on_key_up(self, keyboard, key):
        pass

    def poll(self):
        pass
