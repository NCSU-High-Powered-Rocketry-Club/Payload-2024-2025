"""Module which provides a high level interface to the payload system on the rocket."""
import time
from typing import TYPE_CHECKING

from payload.data_handling.data_processor import IMUDataProcessor
from payload.data_handling.logger import Logger
from payload.data_handling.packets.context_data_packet import ContextDataPacket
from payload.interfaces.base_imu import BaseIMU
from payload.hardware.transmitter import Transmitter
from payload.interfaces.base_receiver import BaseReceiver
from payload.state import StandbyState, State
from payload.constants import TRANSMIT_MESSAGE, STOP_MESSAGE, TRANSMISSION_DELAY

if TYPE_CHECKING:
    from payload.data_handling.packets.processed_data_packet import ProcessedDataPacket
    from payload.hardware.imu import IMUDataPacket


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
        "context_data_packet",
        "data_processor",
        "imu",
        "imu_data_packet",
        "logger",
        "processed_data_packet",
        "receiver",
        "shutdown_requested",
        "state",
        "transmitter",
        "transmitting_latch",
    )

    def __init__(
        self,
        imu: BaseIMU,
        logger: Logger,
        data_processor: IMUDataProcessor,
        transmitter: Transmitter,
        receiver: BaseReceiver,
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
        self.data_processor: IMUDataProcessor = data_processor
        self.transmitter: Transmitter = transmitter
        self.receiver: BaseReceiver = receiver

        # The rocket starts in the StandbyState
        self.state: State = StandbyState(self)
        self.shutdown_requested = False
        self.imu_data_packet: IMUDataPacket | None = None
        self.processed_data_packet: ProcessedDataPacket | None = None
        self.context_data_packet: ContextDataPacket | None = None

        self.transmitting_latch = False

    def start(self) -> None:
        """
        Starts logger processes. This is called before the main while loop starts.
        """
        self.receiver.start()
        self.logger.start()

    def stop(self) -> None:
        """
        Handles shutting down the payload. This will cause the main loop to break. It stops the IMU
        and stops the logger.
        """
        if self.shutdown_requested:
            return
        self.imu.stop()
        self.receiver.stop()
        if self.transmitter:
            self.transmitter.stop()
        self.logger.stop()
        self.shutdown_requested = True

    def update(self) -> None:
        """
        Called every loop iteration from the main process. Depending on the current state, it will
        do different things. It is what controls the payload and chooses when to move to the next
        state.
        """

        # We only get one data packet at a time from the IMU as it runs very slowly
        self.imu_data_packet = self.imu.fetch_data()

        # If we don't have a data packet, return early
        # TODO: we might want to handle this differently and let the states decide what to do
        if not self.imu_data_packet:
            return

        # Update the processed data with the new data packet.
        self.data_processor.update(self.imu_data_packet)

        # Get the processed data packet from the data processor
        self.processed_data_packet = self.data_processor.get_processed_data_packet()

        # Update the state machine based on the latest processed data
        self.state.update()

        self.context_data_packet = ContextDataPacket(
            self.state.name[0], self.receiver.latest_message
        )

        # Logs the current state, extension, IMU data, and processed data
        self.logger.log(
            self.context_data_packet,
            self.imu_data_packet,
            self.processed_data_packet,
        )

    def format_data_packet(self, message: "ProcessedDataPacket") -> str:
        res = ""
        res += f"ca: {message.current_altitude}, "
        res += f"vv: {message.vertical_velocity}, "
        res += f"va: {message.vertical_acceleration}, "
        res += f"tsldp: {message.time_since_last_data_packet}, "
        res += f"ma: {message.maximum_altitude}, "
        res += f"p: {message.pitch}, "
        res += f"r: {message.roll}, "
        res += f"y: {message.yaw}, "
        res += f"mv: {message.maximum_velocity}, "
        res += f"lv: {message.landing_velocity}, "
        res += f"cs: {message.crew_survivability}, "

        return res

    def transmit_data(self) -> None:
        """
        Transmits the processed data packet to the ground station using the transmitter.
        """
        # We check here because the mock doesn't have a transmitter
        if self.transmitter:
            message_string = self.format_data_packet(self.processed_data_packet)
            self.transmitter.send_message(message_string)
        else:
            print("No transmitter!")

    def remote_override(self, message: str):
        # This handles the messages the receiver could get
        if message == TRANSMIT_MESSAGE:
            self.transmitting_latch = True
        elif message == STOP_MESSAGE:
            self.transmitting_latch = False
