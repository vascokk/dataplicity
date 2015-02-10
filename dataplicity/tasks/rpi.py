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
        self.pin_list = [7, 11, 12, 13, 15, 16, 18, 22, 29, 31, 32, 33, 35, 36, 37, 38, 40]
        self.set_pins()

    def set_pins(self, settings=None):
        if not settings:
            settings = self.get_settings('gpio')

        for pin in self.pin_list:
            pin_setting = settings.get('pins', 'pin{}'.format(pin))
            if pin_setting == 'on':
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, 1)
            elif pin_setting == 'off':
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, 0)
            elif pin_setting == 'input':
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin, GPIO.BOTH, callback=self.sample_input, bouncetime=200)

    @onsignal('settings_update', 'gpio')
    def on_settings_update(self, name, settings):
        self.set_pins(settings)

    def sample_input(self, pin):
        print 'pin {} pressed'.format(pin)


class SampleGPIOInputs(Task):
    def on_startup(self):
        GPIO.setmode(GPIO.BOARD)
        pin_list = [8, 10, 12, 13, 15, 16, 18, 22]
        pin_list_b_plus = [29, 31, 32, 33, 35, 36, 37, 38, 40]
        pin_list.extend(pin_list_b_plus)

        for channel in pin_list:
            try:
                GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(channel, GPIO.BOTH, callback=self.sample_input)
            except ValueError:
                pass

    def sample_input(self, channel):
        pass


class DashControlledCamera(Task):
    """Take a photo with the Raspberry Pi camera, controlled by the dashboard element"""

    def init(self):
        """Initialize the task"""
        self.timeline_name = self.conf.get('timeline', 'camera')
        self.frame_no = 1
        self.next_pic = None  # Time to take next pic

    def poll(self):

        now = datetime.datetime.utcnow()
        if self.next_pic is None or now > self.next_pic:
            camera = None
            try:

                try:
                    camera = picamera.PiCamera()
                    camera.resolution = (640, 480)
                except picamera.PiCameraError:
                    self.log.warning("Camera is not enabled. Try running 'sudo raspi-config'")
                    return
                else:
                    self.log.debug('Raspberry Pi camera started')

                settings = self.get_settings('rpi_camera')
                last_pic = settings.get('camera', 'last_pic')
                frequency = settings.get('camera', 'frequency')

                if self.next_pic is None:
                    self.next_pic = now

                while self.next_pic <= now:
                    self.next_pic += timedelta(seconds=int(frequency) * 60)

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

            finally:
                if camera is not None:
                    try:
                        camera.close()
                    except:
                        self.log.exception('error closing camera')
