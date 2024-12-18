import threading
import paramiko
import time
import os
from typing import List

class ThreadStopException(Exception):
    """Custom exception to stop the thread."""
    pass


class CommandExecutor(threading.Thread):
    def __init__(self, ip: str, port: int, delay: int, ios: List[str], username: str = "root", password: str = "evertz"):
        super().__init__()
        self.ip = ip
        self.port = port
        self.delay = delay
        self.ios = ios
        self.username = username
        self.password = password
        self.error = False
        self.end_event = threading.Event()
        try:
            self.transport = paramiko.Transport((self.ip, self.port))
            self.transport.start_client()
            self.transport.auth_password(self.username, self.password)
            if not self.transport.is_authenticated():
                raise paramiko.SSHException("SSH authentication failed.")
        except Exception as connection_error:
            raise paramiko.SSHException(f"Failed to connect to {self.ip}:{self.port} with error: {connection_error}")

        self.channel = self.transport.open_session()
        self.channel.get_pty(term='vt100', width=300, height=24)
        self.channel.invoke_shell()
        self._read_until() # Flush the buffer

    def log(self, msg):
        print(msg)

    def run(self):
        """Main method to run the SSH commands and handle the process."""
        try:
            self._execute_commands()
        except ThreadStopException as e:
            self.log("Automation stopped before completion :(")
            return
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.log("Transport Closed")
            self.channel.close()
            self.transport.close()

    def _read_until(self, expected: str = None, wait_time=2):
        """Read from the channel until the expected text is found or no data available for 2 seconds."""
        start = time.time()
        reply = bytearray()
        last_read_time = start
        while True:
            if self.channel.recv_ready():
                reply.extend(self.channel.recv(8192))
                last_read_time = time.time()
                if expected and expected in reply.decode('utf-8'):
                    break
            elif time.time() - last_read_time > wait_time:  # No data for 2 second
                break
        return reply

    def _send_command(self, command: str, decode_method='utf-8', expected: str=None) -> str:
        """Send a command to the SSH channel and wait for the expected output."""
        if self.end_event.is_set():  # Check if stop signal is received
            raise ThreadStopException("Automation stopped before completion :(")
        self.channel.send(command + '\n')
        out = self._read_until(expected).decode(decode_method).replace('\r', '')
        self.log("+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")
        self.log(f"Command: {command}")
        self.log(f"Output:\n{out}")
        self.log("+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")
        time.sleep(self.delay)
        return out

    def _execute_commands(self):
        """Execute the sequence of commands as per the provided instructions."""
        self._send_command("cd /evertz/test/nexx-xc")
        out = self._send_command("chmod +x routeall.sh")
        if "No such file or directory" in out:
            self.log("\n\nError while executing chmod: No such file or directory")
            raise paramiko.SSHException("File 'routeall.sh' does not exist")
        self._send_command("./routeall.sh")

        for io in self.ios:
            if "B".lower() in io.lower():
                continue
            self._send_command(f"ssh {io}")
            self._send_command("regif fs.ifce.fs_tg_en[0:7]=0xaa")
            self._send_command("exit")

        cmds = ["bfshell", "ucli", "pm", "port-error-clear", "exit", "exit"]
        for cmd in cmds:
            self._send_command(cmd)

        self._send_command('for i in {1..12}; do echo "slot $i:"; ssh xio$i "cd /x45/scripts; ./cge_stat.sh | grep uncorrected"; done > errors-before.temp')
        print("Now waiting 30 seconds")
        time.sleep(30)
        self._read_until()
        cmds = ["bfshell", "ucli", "pm", "port-error-show", "exit", "exit"]
        for cmd in cmds:
            self._send_command(cmd)

        self._send_command('for i in {1..12}; do echo "slot $i:"; ssh xio$i "cd /x45/scripts; ./cge_stat.sh | grep uncorrected"; done > errors-after.temp')

    def stop(self):
        try:
            self.end_event.set()
            self.transport.close()
        except Exception as e:
            print(f"Error while stopping the thread: {e}")


if __name__ == '__main__':
    executor = CommandExecutor("172.17.200.180", 22, 5, ["XIO01A", "X", "Y"])

