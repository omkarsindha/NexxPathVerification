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
        self.channel = None

    def _read_until(self, expected: str, timeout: int = None) -> str:
        """Read from the channel until the expected text is found or the timeout expires."""
        start = time.time()
        reply = bytearray()
        while not self.channel.exit_status_ready():
            if self.channel.recv_ready():
                reply.extend(self.channel.recv(8192))
                if expected and expected in reply.decode('utf-8'):
                    break
            elif timeout and time.time() - start > timeout:
                break
            time.sleep(0.1)
        return reply.decode('utf-8')

    def run(self):
        """Main method to run the SSH commands and handle the process."""
        try:
            transport = paramiko.Transport((self.ip, self.port))
            transport.start_client()
            transport.auth_password(self.username, self.password)
            if not transport.is_authenticated():
                raise paramiko.SSHException("Authorization failed.")
            self.channel = transport.open_session()
            self.channel.get_pty(term='vt100', width=300, height=24)
            self.channel.invoke_shell()
            self.execute_commands()
            transport.close()
            self._download_files()
            self._open_files()
        except paramiko.SSHException as err:
            self.error = True
            print(f"SSHException: {err}")

    def _send_command(self, command: str, expected: str, timeout: int = 10) -> str:
        """Send a command to the SSH channel and wait for the expected output."""
        self.channel.send(command + '\n')
        out = self._read_until(expected, timeout)
        print(f"Command: {command}")
        print(f"Output:\n{out}")
        print("+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+\n\n")
        return out

    def execute_commands(self):
        """Execute the sequence of commands as per the provided instructions."""
        self._send_command("cd /evertz/test/nexx-xc", "#")
        out = self._send_command("chmod +x routeall.sh", "#")
        if "No such file or directory" in out:
            print("\n\nError while executing chmod: No such file or directory")
            raise paramiko.SSHException("No such file or directory")
        self._send_command("./routeall.sh", "#")

        for io in self.ios:
            self._send_command(f"ssh {io}", "#")
            self._send_command("regif fs.ifce.fs_tg_en[0:7]=0xaa", "#")
            self._send_command("exit", "#")

        cmds = ["bfshell", "ucli", "pm", "port-error-clear", "\x01d", "exit"]
        for cmd in cmds:
            self._send_command(cmd, "#")

        self._send_command('for i in {1..12}; do echo "slot $i:"; ssh xio$i "cd /x45/scripts; ./cge_stat.sh | grep uncorrected"; done > errors-before.temp', "#")
        time.sleep(600)

        cmds = ["bfshell", "ucli", "pm", "port-error-show", "\x01d", "exit"]
        for cmd in cmds:
            self._send_command(cmd, "#")

        self._send_command('for i in {1..12}; do echo "slot $i:"; ssh xio$i "cd /x45/scripts; ./cge_stat.sh | grep uncorrected"; done > errors-after.temp', "#")

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
    executor.start()
    executor.join()
