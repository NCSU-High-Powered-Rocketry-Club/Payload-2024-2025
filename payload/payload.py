"""Module which provides a high level interface to the payload system on the rocket."""

from collections import deque
from typing import TYPE_CHECKING

from payload.data_handling.data_processor import IMUDataProcessor
from payload.data_handling.logger import Logger
from payload.hardware.imu import IMU
from payload.state import StandbyState, State

if TYPE_CHECKING:
    from payload.data_handling.processed_data_packet import ProcessedDataPacket
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
        "data_processor",
        "imu",
        "imu_data_packet",
        "logger",
        "processed_data_packets",
        "shutdown_requested",
        "state",
    )

    def __init__(
        self,
        imu: IMU,
        logger: Logger,
        data_processor: IMUDataProcessor,
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
        self.imu = imu
        self.logger = logger
        self.data_processor = data_processor

        # The rocket starts in the StandbyState
        self.state: State = StandbyState(self)
        self.imu_data_packet: IMUDataPacket | None = None
        self.processed_data_packets: list[ProcessedDataPacket] = []
        logger.start()

    def start(self) -> None:
        """
        Starts the IMU and logger processes. This is called before the main while loop starts.
        """
        self.imu.start()
        self.logger.start()

    def stop(self) -> None:
        """
        Handles shutting down the airbrakes. This will cause the main loop to break. It retracts
        the airbrakes, stops the IMU, and stops the logger.
        """


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

        # Logs the current state, extension, IMU data, and processed data
        self.logger.log(
            self.state.name,
            self.imu_data_packet,
            self.processed_data_packet,
        )
