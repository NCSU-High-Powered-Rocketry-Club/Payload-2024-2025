from RPi import GPIO 

target_pin = 1;

def setup_gpio():
    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
    GPIO.setup(target_pin, GPIO.OUT, initial=GPIO.LOW)

def pull_high(target):
    GPIO.output(target, GPIO.HIGH);

def pull_low(target):
    GPIO.output(target, GPIO.LOW);

def main() -> None:
    setup_gpio();
    print("1 -- GPIO High")
    print("2 -- GPIO Low")
   
    while(True):
        

        inp = input("Please choose a command from the above:  ");

        if(inp == "1"):
            pull_high(target_pin)
            print("GPIO " + str(target_pin) + " set high.");
        elif(inp == "2"):
            pull_low(target_pin)
            print("GPIO " + str(target_pin) + " set high.");
        else:
            print("Invalid input");

if __name__ == "__main__":

    main();