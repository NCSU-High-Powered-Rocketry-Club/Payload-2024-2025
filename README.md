# Tacho Lycos 2023-2024 Payload Code

There are guidelines on how code should be structured and uploaded to this repository.


## Setting Up Your Python Venv

The first thing you should do prior to running your code is set up your virtual environment. To do this open you your terminal and make sure you are in the `Payload-2023-2024` directory. Inside of that directory call the commands

(Install pip3)
```bash
sudo apt install python3-pip
```

(Install venv)
```bash
sudo apt install python3-venv
```

(Make venv)
```bash
python3 -m venv env
```

to set up your virtual environment in a folder called env. Next you need to set this folder as your interpreter (your IDE might prompt you to do this automatically. If it did not prompt you, to do this in VS Code, press `ctrl+shift+p` to open your command prompt and type in `Python: Select Interpreter`. Press enter and select the one that ends in something like `('env':venv)`.

## Installing Required Packages

In order to install the required packages, open a new terminal in VS Code by pressing ```ctrl+shift+` ```. This terminal will already be in your virtual environment, and simply run the command

```bash
pip3 install -r requirements.txt
```

## Running the Program

Now that you have all the required packages installed, you can run the program by running the command

```bash
python3 main.py
```

or with arguments

```bash
python3 main.py <arguments>
```

