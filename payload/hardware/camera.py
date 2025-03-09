"""Module to handle video recording of the payload with a camera."""

import os
from contextlib import suppress
from threading import Event, Thread

from payload.constants import CAMERA_SAVE_PATH, CAMERA_START_RECORDING_TIMEOUT, CAMERA_STOP_RECORDING_TIMEOUT

# These libraries are only available on the Raspberry Pi so we ignore them if they are not available
with suppress(ImportError):
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import CircularOutput


class Camera:
    """
    This is the class used to interact with the camera on our rocket. It records on a separate
    thread.
    """

    __slots__ = ("camera_control_thread", "motor_burn_started", "stop_context_event")

    def __init__(self):
        self.stop_context_event = Event()
        self.motor_burn_started = Event()
        self.camera_control_thread = Thread(target=self._camera_control_loop, name="Camera thread")

    @property
    def is_running(self):
        """Returns whether the camera is currently recording."""
        return self.camera_control_thread.is_alive()

    def start(self):
        """Start the video recording, with a buffer. This starts recording in a different thread."""
        self.camera_control_thread.start()

    def stop(self):
        """Stop the video recording."""
        self.motor_burn_started.set()  # in case we stop before motor burn
        self.stop_context_event.set()
        self.camera_control_thread.join()

    def start_recording(self):
        """Start recording when motor burn has started."""
        self.motor_burn_started.set()

    # ------------------------ ALL METHODS BELOW RUN IN A SEPARATE THREAD -------------------------
    def _camera_control_loop(self):
        """Controls the camera recording thread."""
        # set logging level-
        os.environ["LIBCAMERA_LOG_LEVELS"] = "ERROR"

        try:
            camera = Picamera2()
            # Make the camera look good in daylight:
            camera.set_controls({"AwbEnable": True, "AwbMode": "Daylight"})
            # We use the H264 encoder and a circular output to save the video to a file.
            encoder = H264Encoder()
            # The circular output is a buffer with a default size of 150 bytes? which according to
            # the docs is enough for 5 seconds of video at 30 fps.
            output = CircularOutput()
            # Create a basic video configuration
            camera.configure(camera.create_video_configuration())

            # Start recording with the buffer. This operation is non-blocking.
            camera.start_recording(encoder, output)

            # Check if motor burn has started, if it has, we can stop buffering and start saving
            # the video. This way we get a few seconds of video before liftoff too. Otherwise, just
            # sleep and wait.
            self.motor_burn_started.wait(timeout=CAMERA_START_RECORDING_TIMEOUT)

            output.fileoutput = CAMERA_SAVE_PATH
            output.start()

            # Keep recording until we have landed:
            self.stop_context_event.wait(timeout=CAMERA_STOP_RECORDING_TIMEOUT)

            output.stop()
        except Exception as e:
            print(f"Got error {e} while starting the camera.")
