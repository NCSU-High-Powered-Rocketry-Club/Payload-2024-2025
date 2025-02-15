# Tacho Lycos 2024-2025 Payload Code

# Table of Contents

- [Overview](#overview)
- [Design](#design)
- [File Structure](#file-structure)
- [Quick Start](#quick-start)
- [Local Setup](#local-setup)
  - [1. Clone the repository](#1-clone-the-repository)
  - [2. Install the project](#2-install-the-project)
  - [3. Install the pre-commit hook](#3-install-the-pre-commit-hook)
  - [4. Make your changes and commit](#4-make-your-changes-and-commit)
- [Advanced Local Usage](#advanced-local-usage)
  - [Running Mock Launches](#running-mock-launches)
  - [Running Tests](#running-tests)
  - [Running the Linter](#running-the-linter)
- [Pi Usage](#pi-usage)
  - [Connecting to the Pi (SSH)](#connecting-to-the-pi-ssh)
  - [Install and start the pigpio daemon on the Raspberry Pi](#install-and-start-the-pigpio-daemon-on-the-raspberry-pi)
  - [Run a real flight with real hardware](#run-a-real-flight-with-real-hardware)
  - [Running Test Scripts](#running-test-scripts)
- [Contributing](#contributing)
- [License](#license)


## Overview
This project is for the NASA Student Launch competition where our Payload has to transmit and receive data related to the STEMnauts, and various flight metrics. It must transmit the data upon landing, and have an option of a remote override to transmit the data at any point in the flight. We have a Raspberry Pi 4 as the brains of our system which runs our code. It  connects to an IMU (basically an altimeter, accelerometer, gyroscope, magnetometer). The code follows the [finite state machine](https://www.tutorialspoint.com/design_pattern/state_pattern.htm) design pattern, using the ``PayloadContext`` to manage interactions between the states, hardware, logging, and data processing. 


### Design
As per the finite state machine design pattern, we have a context class which links everything together. Every loop, the context:

1. **Gets data from the IMU**
2. **Processes the data** in the Data Processor (calculates velocity, maximums, etc.)
3. **Updates the current state** with the processed data
4. **Logs all data** from the IMU, Data Processor, Servo, and States


### File Structure

We have put great effort into keeping the file structure of this project organized and concise. Try to be intentional on where you place new files or directories.
```
Payload-2024-2025/
├── payload/
|   ├── hardware/
│   │   ├── [files related to the connection of the pi with hardware ...]
|   ├── mock/
│   │   ├── [files related to the connection of mock (or simulated) hardware ...]
|   ├── data_handling/
│   │   ├── [files related to the processing of data ...]
|   ├── interfaces/
│   │   ├── [files which are building blocks to other files]
│   ├── [files which control the payload at a high level ...]
|   ├── main.py [main file used to run on the rocket]
|   ├── constants.py [file for constants used in the project]
├── logs/  [log files made by the logger]
│   ├── ...
├── launch_data/  [real flight data collected from the rocket]
│   ├── ...
├── scripts/  [small files to test individual components like the transmitter]
│   ├── ...
├── pyproject.toml [configuration file for the project]
├── README.md
```

## Quick Start

This project strongly recommends using [`uv`](https://docs.astral.sh/uv/) to manage and install
the project. To quickly run the mock replay, simply run:

```bash
uvx --from git+https://github.com/NCSU-High-Powered-Rocketry-Club/Payload-2024-2025.git mock
```

You should see the mock replay running with a display!

_Note: We will continue using `uv` for the rest of this README._

## Local Setup

If you want to contribute to the project, you will need to set up the project locally. Luckily, 
the only other thing you need to install is [`git`](https://git-scm.com/) for version control.

### 1. Clone the repository:

```
git clone https://github.com/NCSU-High-Powered-Rocketry-Club/Payload-2024-2025.git
cd Payload-2024-2025/
```

### 2. Install the project:
```bash
uv run mock
```

This will install the project, including development dependencies, activate the virtual environment and run the mock replay.

_Note: It is important to use `uv run` instead of `uvx` since the `uvx` environment is isolated from
the project. See the [uv documentation](https://docs.astral.sh/uv/concepts/tools/#relationship-to-uv-run) for more information._

_Note 2: The more "correct" command to run is `uv sync`. This will install the project and its dependencies, but not run the mock replay._

### 3. Install the pre-commit hook:
```
uv run pre-commit install
```
This will install a pre-commit hook that will run the linter before you commit your changes.

### 4. Make your changes and commit:

After you have made your changes, you can commit them:
```bash
git add .
git commit -m "Your commit message"
```

You will see the linter run now. If one of the checks failed, you can resolve them by following the 
instructions in [Running the Linter](#running-the-linter).

```bash
git push -u origin branch-name
```

## Advanced Local Usage

### Running Mock Launches
Testing our code can be difficult, so we've developed a way to run mock launches based on previous flight data--the rocket pretends, in real-time, that it's flying through a previous launch.

To run a mock launch, run:
```bash
uv run mock
```
If you want to run a mock launch, but with the real transmitter running, run:
```bash
uv run mock -t
```
There are some additional options you can use when running a mock launch. To view them all, run:
```bash
uv run mock --help
```

### Running Tests
Our CI pipeline uses [pytest](https://pytest.org) to run tests. You can run the tests locally to ensure that your changes are working as expected.

_Note: Unit tests do not work on Windows (only `test_integration.py` will work)._

To run the tests, run this command from the project root directory:
```bash
uv run pytest
```

If your virtual environment is activated, you can simply run the tests with `pytest`

If you make a change to the code, please make sure to update or add the necessary tests.

### Running the Linter

Our CI also tries to maintain code quality by running a linter. We use [Ruff](https://docs.astral.sh/ruff/).

To run the linter, and fix any issues it finds, run:
```bash
ruff check . --fix --unsafe-fixes
```
To format the code, run:
```bash
ruff format .
```

## Pi Usage

_There are libraries that only fully work when running on the Pi (rpi-gpio, picamera2), so if you're having trouble importing them locally, program the best you can and test your changes on the pi._


### Connecting to the Pi (SSH)
In order to connect to the Pi, you need first to set up a mobile hotspot with the name `HPRC`, password `tacholycos`, and `2.4 GHz` band. Next, turn on the Pi and it will automatically connect to your hotspot. Once it's connected, find the Pi's IP Address, and in your terminal run:
```bash
ssh pi@[IP.ADDRESS]
# Its password is "raspberry"
cd Payload-2024-2025/
```

### Install the dependencies needed for the camera integration:

```bash
sudo apt install libcap-dev libcamera-dev libkms++-dev libfmt-dev libdrm-dev

uv sync --all-groups
```

### Run a real flight with real hardware:
```bash
uv run real
```

### Running Test Scripts
During development, you may want to run individual scripts to test components. For example, to test the servo, run:
```bash
# Make sure you are in the root directory:
uv run scripts/run_pressure_sensor.py
```

## Contributing
Feel free to submit issues or pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the MIT License. You are free to copy, distribute, and modify the software, provided that the original license notice is included in all copies or substantial portions of the software. See LICENSE for more.