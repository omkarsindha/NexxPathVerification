import threading
import paramiko
import time
import os
from typing import List


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
        self.transport = paramiko.Transport((self.ip, self.port))
        self.transport.start_client()
        self.transport.auth_password(self.username, self.password)
        if not self.transport.is_authenticated():
            raise paramiko.SSHException("Authorization failed.")
        self.channel = self.transport.open_session()
        self.channel.get_pty(term='vt100', width=300, height=24)
        self.channel.invoke_shell()
        self._read_until() # Flush the buffer

    def run(self):
        """Main method to run the SSH commands and handle the process."""
        try:
            self._execute_commands()
            self._download_files()
            self._open_files()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.transport.close()

    def _read_until(self, expected: str = None):
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
            elif time.time() - last_read_time > 2:  # No data for 2 second
                break
        return reply

    def _send_command(self, command: str, decode_method='utf-8', expected: str=None) -> str:
        """Send a command to the SSH channel and wait for the expected output."""
        # Flush existing data in channel first
        self.channel.send(command + '\n')
        out = self._read_until(expected).decode(decode_method).replace('\r', '')
        print("+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")
        print(f"Command: {command}")
        print(f"Output:\n{out}")
        print("+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")
        time.sleep(self.delay)
        return out

    def _execute_commands(self):
        """Execute the sequence of commands as per the provided instructions."""
        self._send_command("cd /evertz/test/nexx-xc")
        out = self._send_command("chmod +x routeall.sh")
        if "No such file or directory" in out:
            print("\n\nError while executing chmod: No such file or directory")
            raise paramiko.SSHException("File 'routeall.sh' does not exist")
        self._send_command("./routeall.sh")

        for io in self.ios:
            self._send_command(f"ssh {io}")
            self._send_command("regif fs.ifce.fs_tg_en[0:7]=0xaa")
            self._send_command("exit")

        cmds = ["bfshell", "ucli", "pm", "port-error-clear", "exit", "exit"]
        for cmd in cmds:
            self._send_command(cmd)

        self._send_command('for i in {1..12}; do echo "slot $i:"; ssh xio$i "cd /x45/scripts; ./cge_stat.sh | grep uncorrected"; done > errors-before.temp')
        time.sleep(600)

        cmds = ["bfshell", "ucli", "pm", "port-error-show", "exit", "exit"]
        for cmd in cmds:
            self._send_command(cmd)

        self._send_command('for i in {1..12}; do echo "slot $i:"; ssh xio$i "cd /x45/scripts; ./cge_stat.sh | grep uncorrected"; done > errors-after.temp')

    def _download_files(self):
        """Download the error files from the remote server to the local machine."""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, self.port, self.username, self.password)
            sftp = ssh.open_sftp()
            remote_files = ["/evertz/test/nexx-xc/errors-before.temp", "/evertz/test/nexx-xc/errors-after.temp"]
            for remote_file in remote_files:
                try:
                    local_file = os.path.basename(remote_file)
                    sftp.get(remote_file, local_file)
                    print(f"Downloaded {remote_file} to {local_file}")
                except FileNotFoundError:
                    print(f"File not found: {remote_file}")
                except IOError as e:
                    print(f"IOError while downloading {remote_file}: {e}")
            sftp.close()
            ssh.close()
        except Exception as e:
            print(f"An error occurred: {e}")

    @staticmethod
    def _open_files():
        """Open the downloaded files using notepad."""
        def run_code(text_editor_command: str, file_path: str):
            os.system(f"{text_editor_command} {file_path}")

        file_paths = ["errors-before.temp", "errors-after.temp"]
        for file in file_paths:
            edit_thread = threading.Thread(target=run_code, args=("notepad", file))
            edit_thread.start()


if __name__ == '__main__':
    executor = CommandExecutor("172.17.200.180", 22, 5, ["XIO01A", "X", "Y"])

