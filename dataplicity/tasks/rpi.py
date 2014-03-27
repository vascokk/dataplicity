from dataplicity.client.task import Task

from io import BytesIO

try:
	import picamera
except:
	import sys
	# Attempt a friendly error message
	sys.stderr.write("Python module 'picamera' is required for this example")
	raise


class TakePhoto(Task):
	"""Take a photo with the Raspberry Pi camera"""

	def init(self):
		self.timeline_name = self.conf.get('timeline', 'camera')
		self.camera = picamera.PiCamera()
		self.camera.resolution = (1024, 768)
		self.camera.start_preview()
		self.frame_no = 1
		self.log.debug('Raspberry Pi camera started')
		self.log.debug('Say CHEESE!')

	def poll(self):
		filename = "rpi{!06}.jpg".format(self.frame_no)
		camera_file = BytesIO()
		self.camera.capture(camera_file, 'jpeg')

		timeline = self.client.get_timeline(self.timeline_name)
		event = timeline.new_photo(text="Captured by the Raspberry Pi Camera",
		                           file=camera_file,
		                           filename=filename)
		event.write()
		self.frame_no += 1
