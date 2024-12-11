import time
import paramiko


class Config:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.IOs = []  #
        self.load_ios()


    def load_ios(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.ip, port=self.port, username="root", password="evertz", timeout=3)
        chan = ssh.get_transport().open_session()
        chan.get_pty()
        chan.exec_command("{ forallx -a uptime -p|sed 's/^/A:/g' & forallx -b uptime -p | sed 's/^/B:/g' & } | sort " +
                          "-t: -k1,1 | cut -d: -f1-2,4- | column -s: -t")
        result = ""
        while chan.exit_status_ready() is False:
            time.sleep(0.1)

        if chan.recv_ready() is True:
            result += chan.recv(4096).decode("utf-8")
        chan.close()
        ssh.close()

        lines = result.split('\n')
        filtered_lines = [line for line in lines if line.strip()]
        for item in filtered_lines:
            parts = item.split()
            result = parts[1] + parts[0]
            self.IOs.append(result)
        for io in self.IOs:
            if "XXC" in io:
                self.IOs.remove(io)


if __name__ == "__main__":
    config_instance = Config("172.17.200.180", 22)
    print(config_instance.IOs)
    print(config_instance.CMDs)
    print(config_instance.IO_CMDs)

