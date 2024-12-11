import threading
import paramiko
import time


class CommandExecutor(threading.Thread):
	def __init__(self, ip, port, delay, ios, username = "root", password = "evertz"):
		super().__init__()
		self.ip = ip
		self.port = port
		self.delay = delay
		self.username = username
		self.password = password
		self.error = False

	@staticmethod
	def read_until(channel, expected, timeout=None):
		"""Read from the channel until the expected text is found or the timeout expires."""
		start = time.time()
		reply = bytearray()
		while not channel.exit_status_ready():
			if channel.recv_ready():
				reply.extend(channel.recv(8192))
				if expected and expected in reply:
					break
			elif timeout and time.time() - start > timeout:
				break
			time.sleep(0.1)
		return reply.decode('utf-8')

	def run(self):
		try:
			transport = paramiko.Transport((self.ip, self.port))
			transport.start_client()
			transport.auth_password(self.username, self.password)
			if not transport.is_authenticated():
				raise paramiko.SSHException("Authorization failed.")

			channel = transport.open_session()
			channel.get_pty(term='vt100', width=300, height=24)
			channel.invoke_shell()
			self.execute_commands(channel)
			transport.close()
		except paramiko.SSHException as err:
			self.error = True

	def execute_commands(self, channel):
		"""Send a list of commands to the SSH channel."""
		out = self.read_until("cd /evertz/text/nexx-cc")

