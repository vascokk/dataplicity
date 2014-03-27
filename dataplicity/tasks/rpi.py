from dataplicity.client.task import Task

from io import BytesIO

try:
	import picamera
except:
	import sys
	# Attempt a friendly error message
	sys.stderr.write("Python module 'picamera' is required for this example\n")
	raise


class TakePhoto(Task):
	"""Take a photo with the Raspberry Pi camera"""

	def init(self):
		"""Initialize the task"""
		self.camera = self.start_camera()
		self.timeline_name = self.conf.get('timeline', 'camera')
		self.frame_no = 1
		self.log.debug('Raspberry Pi camera started')
		self.log.debug('Say CHEESE!')

	def start_camera(self):
		"""Start the camera and return the camera instance"""
		camera = picamera.PiCamera()
		camera.resolution = (1024, 768)
		camera.start_preview()
		return camera

	def poll(self):
		# Write a frame to memory
		camera_file = BytesIO()
		self.camera.capture(camera_file, 'jpeg')

		# Get the timeline
		timeline = self.client.get_timeline(self.timeline_name)

		# Create a new event photo
		event = timeline.new_photo(text="Captured by the Raspberry Pi Camera",
		                           file=camera_file,
		                           name="photo_{:06}".format(self.frame_no),
		                           ext="jpeg")
		# Write the event
		event.write()
		# Keep track of the frame number
		self.frame_no += 1
