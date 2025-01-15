"""Module which provides a high level interface to the payload system on the rocket."""

from collections import deque
from typing import TYPE_CHECKING

from payload.data_handling.data_processor import IMUDataProcessor
from payload.data_handling.imu_data_packet import EstimatedDataPacket
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
        "est_data_packets",
        "imu",
        "imu_data_packets",
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
        self.shutdown_requested = False
        self.imu_data_packets: deque[IMUDataPacket] = deque()
        self.processed_data_packets: list[ProcessedDataPacket] = []
        self.est_data_packets: list[EstimatedDataPacket] = []

    def start(self) -> None:
        """
        Starts the IMU and logger processes. This is called before the main while loop starts.
        """
        self.imu.start()
        self.logger.start()

    def stop(self) -> None:
        """
        Handles shutting down the payload. This will cause the main loop to break. It stops the IMU
        and stops the logger.
        """
        if self.shutdown_requested:
            return
        self.imu.stop()
        self.logger.stop()
        self.shutdown_requested = True

    def update(self) -> None:
        """
        Called every loop iteration from the main process. Depending on the current state, it will
        do different things. It is what controls the payload and chooses when to move to the next
        state.
        """
        # get_imu_data_packets() gets from the "first" item in the queue, i.e, the set of data
        # *may* not be the most recent data. But we want continuous data for state and logging
        # purposes, so we don't need to worry about that, as long as we're not too behind on
        # processing
        self.imu_data_packets = self.imu.get_imu_data_packets()

        # This happens quite often, on our PC's since they are much faster than the Pi.
        if not self.imu_data_packets:
            return

        # Split the data packets into estimated and raw data packets for use in processing and
        # logging
        self.est_data_packets = [
            data_packet
            for data_packet in self.imu_data_packets
            if isinstance(data_packet, EstimatedDataPacket)
        ]

        # Update the processed data with the new data packets. We only care about EstDataPackets
        self.data_processor.update(self.est_data_packets)

        # Get the processed data packets from the data processor, this will have the same length
        # as the number of EstimatedDataPackets in data_packets
        if self.est_data_packets:
            self.processed_data_packets = self.data_processor.get_processed_data_packets()

        # Update the state machine based on the latest processed data
        self.state.update()

        # Logs the current state, extension, IMU data, and processed data
        self.logger.log(
            self.state.name,
            self.imu_data_packets,
            self.processed_data_packets,
        )
