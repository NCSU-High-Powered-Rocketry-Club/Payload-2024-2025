from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import FlightStats

import serial
import sounddevice as sd
import soundfile as sf

import logging
import time
import subprocess


class RadioPTT:
    """Helper Class to trigger and un-trigger PTT (Push-to-talk)"""

    def __init__(self, ptt_port: str) -> None:
        # self.ptt = serial.Serial(ptt_port)
        ...

    def __enter__(self) -> RadioPTT:
        # self.ptt.rts = True
        # self.ptt.dtr = False

        # time.sleep(1)  # Give it time to start transmiting
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # self.ptt.rts = False
        # self.ptt.dtr = True
        ...


class RFInterface:

    # Name of the file to save our audio as
    AUDIO_FILE_NAME = "sensor_audio.wav"

    # Name of the audio device to play. Will try and match a substring
    AUDIO_DEVICE_SUBSTR = "All"

    def __init__(self, callsign: str, ptt_port: str):
        self.callsign = callsign
        self.ptt = RadioPTT(ptt_port)

    def transmit_data(self, data: FlightStats):
        logging.info("Generating TTS...")

        cmd = (
            "espeak",
            "-w",
            f"{self.AUDIO_FILE_NAME}",
            f'"This is {self.callsign}-1 for Student Launch. {str(data)} This is {self.callsign}-1. "',
        )

        subprocess.call(cmd, shell=True)
        logging.info("Reading audio file...")
        audio, samplerate = sf.read(self.AUDIO_FILE_NAME)

        logging.info("Speaking...")

        with self.ptt:
            # play audio file and block
            sd.play(audio, samplerate, device=self.AUDIO_DEVICE_SUBSTR)
            sd.wait()

        # 'with' block automatically triggers and releases PTT
        logging.info("Done speaking.")


# For testing the radio interface and PTT
if __name__ == "__main__":
    interface = RFInterface("hello", "")
    interface.transmit_data(None)
