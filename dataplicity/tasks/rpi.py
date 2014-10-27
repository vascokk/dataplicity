from dataplicity.client.task import Task, onsignal
from dataplicity import atomicwrite

from io import BytesIO
import datetime
from datetime import timedelta

try:
    import picamera
except:
    import sys
    # Attempt a friendly error message
    sys.stderr.write("Python module 'picamera' is required for this example\n")
    sys.stderr.write("Try 'sudo pip install picamera'")
    raise

try:
    import RPi.GPIO as GPIO
except:
    import sys
    sys.stderr.write("Python module 'RPi.GPIO' is required for this example\n")
    sys.stderr.write("Try 'sudo pip install RPi.GPIO'")
    raise


class TakePhoto(Task):
    """Take a photo with the Raspberry Pi camera"""

    def init(self):
        """Initialize the task"""
        self.timeline_name = self.conf.get('timeline', 'camera')
        self.frame_no = 1
        self.camera = None

    def on_startup(self):
        """Start the camera and return the camera instance"""
        self.camera = camera = picamera.PiCamera()
        camera.resolution = (640, 480)
        self.log.debug('Raspberry Pi camera started')

    def on_shutdown(self):
        # Gracefully close the camera
        self.camera.close()

    def poll(self):
        # Write a frame to memory
        self.log.debug('Say CHEESE!')
        camera_file = BytesIO()
        self.camera.capture(camera_file, 'jpeg')

        # Get the timeline
        timeline = self.client.get_timeline(self.timeline_name)

        # Create a new event photo
        event = timeline.new_photo(camera_file,
                                   title="Frame {:06}".format(self.frame_no),
                                   text="Captured by the Raspberry Pi Camera",
                                   ext="jpeg")
        # Write the event
        event.write()
        # Keep track of the frame number
        self.frame_no += 1


class SetGPIO(Task):
    def on_startup(self):
        GPIO.setmode(GPIO.BOARD)
        self.pin_list = [7, 11, 12, 13, 15, 16, 18, 22]
        for pin in self.pin_list:
            GPIO.setup(pin, GPIO.OUT)

    @onsignal('settings_update', 'gpio')
    def on_settings_update(self, name, settings):
        for pin in self.pin_list:
            pin_setting = settings.get('pins', 'pin{}'.format(pin))
            if pin_setting == 'on':
                GPIO.output(pin, 1)
            elif pin_setting == 'off':
                GPIO.output(pin, 0)


class DashControlledCamera(Task):
    """Take a photo with the Raspberry Pi camera, controlled by the dashboard element"""

    def init(self):
        """Initialize the task"""
        self.timeline_name = self.conf.get('timeline', 'camera')
        self.frame_no = 1

    def poll(self):
        try:
            camera = picamera.PiCamera()
            camera.resolution = (640, 480)
            self.log.debug('Raspberry Pi camera started')
        except picamera.PiCameraError:
            camera = None
            self.log.debug("Camera is not enabled. Try running 'sudo raspi-config'")

        if camera:
            settings = self.get_settings('rpi_camera')
            last_pic = settings.get('camera', 'last_pic')
            frequency = settings.get('camera', 'frequency')
            now = datetime.datetime.now()

            def write_conf(settings, dt):
                # write new date in config
                settings.set('camera', 'last_pic', dt.strftime('%Y-%m-%d %H:%M'))
                with atomicwrite.open(settings.path, 'wb') as fp:
                    settings.write(fp)

            if last_pic == 'never':
                # no picture taken yet, take one
                take_pic = True
                write_conf(settings, now)
            else:
                if frequency == 'never':
                    take_pic = False
                else:
                    last_pic_dt = datetime.datetime.strptime(last_pic, '%Y-%m-%d %H:%M')
                    if (last_pic_dt + timedelta(minutes=int(frequency))) <= now:
                        take_pic = True
                        write_conf(settings, now)
                    else:
                        take_pic = False

            if take_pic:
                # Write a frame to memory
                self.log.debug('Say CHEESE!')
                camera_file = BytesIO()
                camera.capture(camera_file, 'jpeg')

                # Get the timeline
                timeline = self.client.get_timeline(self.timeline_name)

                # Create a new event photo
                event = timeline.new_photo(camera_file,
                                           title="Frame {:06}".format(self.frame_no),
                                           text="Captured by the Raspberry Pi Camera",
                                           ext="jpeg")
                # Write the event
                event.write()
                # Keep track of the frame number
                self.frame_no += 1

            camera.close()