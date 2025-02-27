"""Module which uses a mock camera, since the original camera needs many libraries and actual
hardware."""

from time import sleep

from payload.hardware.camera import Camera

BYTES_PER_30_SECONDS = 9 * 1024 * 1024  # 9 MB in bytes
BYTES_PER_0_1_SECONDS = BYTES_PER_30_SECONDS / 300  # 30 seconds / 300 = 0.1 seconds


class MockCamera(Camera):
    """Mock the camera class. This class fills an internal buffer with random bytes
    to simulate a real flight. The number of bytes written correspond to a ~24 fps recording.

    Even though this is detached from the actual camera implementation, using a buffer serves
    some purposes:

    1. Tests CPU and memory load, as this is another thread.
    2. Tests that the stop events are working correctly with them.
    """

    __slots__ = ("buffer",)

    def __init__(self):
        super().__init__()
        self.camera_control_thread.name = "Mock Camera Thread"
        # The buffer to hold the video data.
        self.buffer = bytearray()

    def _camera_control_loop(self):
        """Starts the mock camera process"""
        # Wait for the motor burn to start before starting to write to the buffer.
        self.motor_burn_started.wait()

        # our video is 1280x720, roughly 24 fps, 2 bytes per pixel (?). We get about 9 MB video
        # every ~30 seconds.
        while not self.stop_context_event.is_set():
            # Write CAMERA_IDLE_TIMEOUT_SECONDS seconds of video data to the buffer.

            self.buffer.extend(b"0" * int(BYTES_PER_0_1_SECONDS))
            sleep(0.1)
