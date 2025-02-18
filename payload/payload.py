"""Module which provides a high level interface to the payload system on the rocket."""

import time
from typing import TYPE_CHECKING

from payload.constants import NO_MESSAGE_TRANSMITTED, STOP_MESSAGE, TRANSMIT_MESSAGE
from payload.data_handling.data_processor import DataProcessor
from payload.data_handling.logger import Logger
from payload.data_handling.packets.context_data_packet import ContextDataPacket
from payload.hardware.camera import Camera
from payload.hardware.transmitter import Transmitter
from payload.interfaces.base_imu import BaseIMU
from payload.interfaces.base_receiver import BaseReceiver
from payload.state import StandbyState, State

if TYPE_CHECKING:
    from payload.data_handling.packets.processor_data_packet import ProcessorDataPacket
    from payload.hardware.imu import IMUDataPacket
    from payload.interfaces.base_transmitter import BaseTransmitter


class PayloadContext:
    """
    Manages the state machine for the rocket's payload system, keeping track of the current state
    and communicating with hardware like the IMU. This class is what connects the state
    machine to the hardware.

    Read more about the state machine pattern here:
    https://www.tutorialspoint.com/design_pattern/state_pattern.htm
    """

    __slots__ = (
        "_last_transmission_time",
        "_stop_latch",
        "_transmitting_latch",
        "camera",
        "context_data_packet",
        "data_processor",
        "imu",
        "imu_data_packet",
        "logger",
        "processed_data_packet",
        "receiver",
        "shutdown_requested",
        "state",
        "transmitted_message",
        "transmitter",
    )

    def __init__(
        self,
        imu: BaseIMU,
        logger: Logger,
        data_processor: DataProcessor,
        transmitter: Transmitter,
        receiver: BaseReceiver,
        camera: Camera,
    ) -> None:
        """
        Initializes the payload context with the specified hardware objects, logger, and data
        processor. The state machine starts in the StandbyState, which is the initial state of the
        payload system.
        :param imu: The IMU object that reads data from the rocket's IMU. This can be a real IMU or
        a mock IMU.
        :param logger: The logger object that logs data to a CSV file.
        :param data_processor: The data processor object that processes IMU data on a higher level.
        """
        self.imu: BaseIMU = imu
        self.logger: Logger = logger
        self.data_processor: DataProcessor = data_processor
        self.transmitter: BaseTransmitter = transmitter
        self.receiver: BaseReceiver = receiver
        self.camera: Camera = camera

        # The rocket starts in the StandbyState
        self.state: State = StandbyState(self)
        self.shutdown_requested = False
        self.imu_data_packet: IMUDataPacket | None = None
        self.processed_data_packet: ProcessorDataPacket | None = None
        self.context_data_packet: ContextDataPacket | None = None
        self.transmitted_message = NO_MESSAGE_TRANSMITTED

        self._transmitting_latch = False
        self._stop_latch = False

    def start(self) -> None:
        """
        Starts the components of our payload such as the IMU, Transmitter, Receiver, etc. Must be
        called before `self.update()`
        """
        # TODO: make threads safer by using a context manager
        self.imu.start()
        self.transmitter.start()
        self.receiver.start()
        self.logger.start()
        self.camera.start()

    def stop(self) -> None:
        """
        Handles shutting down the payload. This will cause the main loop to break. It stops
        components like the IMU, Logger, Transmitter, Receiver, etc.
        """
        # TODO: make a better way to print out what is stopping
        if self.shutdown_requested:
            return
        self.imu.stop()
        print("Stopped IMU")
        self.receiver.stop()
        print("Stopped Receiver")
        self.transmitter.stop()
        print("Stopped Transmitter")
        self.logger.stop()
        print("Stopped Logger")
        self.camera.stop()
        print("Stopped Camera")
        self.shutdown_requested = True
        print("Stopped Everything")

    def update(self) -> None:
        """
        Called every loop iteration from the main process. Depending on the current state, it will
        do different things. It is what controls the payload and chooses when to move to the next
        state.
        """

        # We only get one data packet at a time from the IMU as it runs very slowly
        self.imu_data_packet = self.imu.fetch_data()

        # If we don't have a data packet, return early
        if not self.imu_data_packet:
            return

        # Update the processed data with the new data packet.
        self.data_processor.update(self.imu_data_packet)

        # Get the processed data packet from the data processor
        self.processed_data_packet = self.data_processor.get_processor_data_packet()

        # Check if we have a message from the ground station
        self.remote_override(self.receiver.latest_message)

        # Update the state machine
        self.state.update()

        # We make a data packet with info about what the context is doing
        self.context_data_packet = ContextDataPacket(
            self.state.name[0],
            self.transmitted_message,
            self.receiver.latest_message,
            time.time_ns(),
        )

        # Logs the current state, extension, IMU data, and processed data
        self.logger.log(
            self.context_data_packet,
            self.imu_data_packet,
            self.processed_data_packet,
        )

    def transmit_data(self) -> None:
        """
        Transmits the processed data packet to the ground station using the transmitter.
        """
        self.transmitted_message = f"start: {self.processed_data_packet}"
        self.transmitter.send_message(self.transmitted_message)

    def start_saving_camera_recording(self) -> None:
        """
        Starts recording the camera when the motor burn has started. See `MotorBurnState`.
        """
        self.camera.start_recording()

    def remote_override(self, message: str):
        """
        Receives a message from the ground station and acts on it.
        :param message: The message received from the ground station.
        """
        if message == TRANSMIT_MESSAGE and not self._transmitting_latch:
            self._transmitting_latch = True
            self._stop_latch = False
            self.transmit_data()
        elif message == STOP_MESSAGE and not self._stop_latch:
            self._stop_latch = True
            self._transmitting_latch = False

    def start_survivability_calculation(self):
        """
        Starts the calculation of crew survivability percent.
        Called upon motor burn out
        """
        self.data_processor.calculating_crew_survivability = True

    def stop_survivability_calculation(self):
        """
        Calls function in data_processor which finalizes the crew
        survivability percentage based on ground hit velocity.
        """
        self.data_processor.calculating_crew_survivability = False
        self.data_processor.finalize_crew_survivability()
