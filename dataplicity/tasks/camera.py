from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.client.task import Task

try:
    import pygame.camera
    import pygame.image
except:
    import sys
    sys.stderr.write('This task required pygame\n')
    raise


import os
import tempfile


class TakePhoto(Task):
    """Take a photo with the Raspberry Pi camera"""

    def init(self):
        """Initialize the task"""
        self.timeline_name = self.conf.get('timeline', 'camera')
        self.frame_no = 1

    def on_startup(self):
        """Start the camera and return the camera instance"""
        pygame.camera.init()
        self.camera = camera = pygame.camera.Camera(pygame.camera.list_cameras()[0])
        camera.start()
        self.log.debug('camera started')

    def on_shutdown(self):
        # Gracefully close the camera
        self.log.debug("shutting down camera")
        pygame.camera.quit()

    def poll(self):
        self.log.debug('Say CHEESE!')
        # Take a photo
        img = self.camera.get_image()
        # We need a temporary file to save the photo
        tmp_filename = tempfile.mktemp('dataplicity_cam') + '.jpg'
        try:
            # Save to photo
            pygame.image.save(img, tmp_filename)

            # Get the timeline
            timeline = self.client.get_timeline(self.timeline_name)

            # Create a new event photo
            event = timeline.new_photo(tmp_filename,
                                       title="Frame {:06}".format(self.frame_no),
                                       text="Captured with Dataplicity camera task",
                                       ext="jpeg")
            # Write the event
            event.write()
            # Keep track of the frame number
            self.frame_no += 1
        finally:
            # Delete the temporary file
            try:
                os.remove(tmp_filename)
            except:
                pass
