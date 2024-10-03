from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .payload import FlightStats

import serial
import sounddevice as sd
import soundfile as sf
import pyttsx3

import logging
import time


class RadioPTT:
    """Helper Class to trigger and un-trigger PTT (Push-to-talk)"""

    def __init__(self, ptt_port: str) -> None:
        self.ptt = serial.Serial(ptt_port)

    def __enter__(self) -> RadioPTT:
        self.ptt.rts = True
        self.ptt.dtr = False

        time.sleep(1)  # Give it time to start transmiting
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.ptt.rts = False
        self.ptt.dtr = True


class RFInterface:
    AUDIO_FILE_NAME = "sensor_audio.wav"
    AUDIO_DEVICE_SUBSTR = "All"

    def __init__(self, callsign: str, ptt_port: str):
        self.callsign = callsign
        self.ptt = RadioPTT(ptt_port)
        self.tts_engine = pyttsx3.init()

    def transmit_data(self, data: FlightStats):
        logging.info("Generating TTS...")

        self.tts_engine.save_to_file(
            f"This is {self.callsign} for Student Launch. "
            f"{str(data)}"
            f"This is {self.callsign}. ",
            self.AUDIO_FILE_NAME,
        )
        self.tts_engine.runAndWait()

        logging.info("Reading audio file...")
        audio, samplerate = sf.read(self.AUDIO_FILE_NAME)

        logging.info("Speaking...")

        with self.ptt:
            # play audio file and block
            sd.play(audio, samplerate, device=self.AUDIO_DEVICE_SUBSTR)
            sd.wait()

        # 'with' block automatically triggers and releases PTT
        logging.info("Done speaking.")
