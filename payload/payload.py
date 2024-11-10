"""Module which provides a high level interface to the payload system on the rocket."""


class PayloadContext:
    """
    Manages the state machine for the rocket's payload system, keeping track of the current state
    and communicating with hardware like the radio and IMU. This class is what connects the state
    machine to the hardware.

    Read more about the state machine pattern here:
    https://www.tutorialspoint.com/design_pattern/state_pattern.htm
    """

    __slots__ = ()

    def __init__(
        self,
    ) -> None:
        """
        Initializes the payload context with the specified hardware objects, logger, and data
        processor. The state machine starts in the StandbyState, which is the initial state of the
        payload system.
        """
        pass

    def start(self) -> None:
        """
        Starts the IMU and logger processes. This is called before the main while loop starts.
        """
        pass

    def stop(self) -> None:
        """
        Handles shutting down the payload. This will cause the main loop to break. It retracts
        the payload, stops the IMU, and stops the logger.
        """
        pass

    def update(self) -> None:
        """
        Called every loop iteration from the main process. Depending on the current state, it will
        do different things. It is what controls the payload and chooses when to move to the next
        state.
        """
        pass
