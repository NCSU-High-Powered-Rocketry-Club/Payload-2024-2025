import subprocess


def restart_direwolf():
    subprocess.run(["pkill", "-f", "direwolf"], check=True)  # Stop Direwolf
    subprocess.run(["sleep", "2"])  # Wait for a couple of seconds
    subprocess.Popen(["direwolf"])  # Restart Direwolf


# Call this function as needed after updating the configuration
restart_direwolf()
