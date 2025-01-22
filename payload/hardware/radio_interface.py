from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .xbee_interface import XbeeInterface


import logging
import subprocess

import sounddevice as sd
import soundfile as sf

from ..spaceducks.shared.state import FlightStats, Message


class RFInterface:
    # Name of the file to save our audio as
    AUDIO_FILE_NAME = "sensor_audio.wav"

    def __init__(self, callsign: str, xbee: XbeeInterface):
        self.callsign = callsign
        self.xbee = xbee

    def transmit_data(self, data: FlightStats):
        logging.info("Generating TTS...")

        cmd = (
            "espeak",
            "-w",
            f"{self.AUDIO_FILE_NAME}",
            f'"This is {self.callsign} for Student Launch. {data!s} This is {self.callsign}. "',
        )

        self.xbee.send_data(Message("Beginning transmission..."))

        subprocess.call(cmd, shell=True)
        logging.info("Reading audio file...")
        audio, samplerate = sf.read(self.AUDIO_FILE_NAME)

        logging.info("Speaking...")

        # play audio file and block
        sd.play(audio, samplerate)
        sd.wait()

        logging.info("Done speaking.")

        self.xbee.send_data(Message("Transmission complete."))


# For testing the radio interface and PTT
if __name__ == "__main__":
    pass
