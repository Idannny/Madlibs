from typing import *
import types
import py_env
import importlib
import importlib.util
import socket
import queue
import threading
import sys
import os
import traceback
import argparse
import copy
from py_env.protocol import TaskDone, Message
from py_env.utils import log, old_stderr, old_stdout
import traceback

class Host:

  def __init__(self, sock : socket.socket, client_addr : Tuple[str, int]):
    self.sock = sock
    self.client_addr = client_addr

    self.host_task_queue = queue.Queue()

    self.stdin_queue = queue.Queue()
    self.out_queue = queue.Queue()

    self.stdin_proxy = py_env.proxy_io.IOProxy(input_queue=self.stdin_queue, output_queue=None)
    self.stdout_proxy = py_env.proxy_io.IOProxy(input_queue=None, output_queue=self.out_queue)
    self.stderr_proxy = py_env.proxy_io.IOProxy(input_queue=None, output_queue=self.out_queue)

    self.stdin_reader = py_env.proxy_io.IOProxyReader(self.stdin_proxy)
    self.stdout_writer = py_env.proxy_io.IOProxyWriter("stdout", self.stdout_proxy)
    self.stderr_writer = py_env.proxy_io.IOProxyWriter("stderr", self.stderr_proxy)

    self.command_handlers = {
      py_env.protocol.LoadCodeByPath: self.for_load_code_by_path,
      py_env.protocol.LoadCode: self.for_load_code
    }

    self.socket_splitter = py_env.proxy_io.SocketSplitter(protocol=py_env.protocol.JsonProtocol(),
                                                          sock=self.sock,
                                                          sock_write_source=self.out_queue,
                                                          sock_stdin_dest=self.stdin_queue,
                                                          sock_stdout_dest=None,
                                                          sock_stderr_dest=None,
                                                          command_handlers=self.command_handlers,
                                                          on_read_handler_exception=self.read_handler_excetion)

  def run(self):
    threading.Thread(target=self.socket_splitter.run).start()
    try:
      while True:
        task = self.host_task_queue.get()
        task()
    except StopIteration:
      pass

  def get_code(self, content : str, filename : str, argv : list, environ : dict, pwd : str):
    os.chdir(pwd)

    code = content
    code = compile(code, filename, "exec")

    mod = types.ModuleType(filename)
    mod.__file__ = filename
    mod.__package__ = ''

    mod_sys_spec = importlib.util.find_spec('sys')
    mod.sys = importlib.util.module_from_spec(mod_sys_spec)
    mod_sys_spec.loader.exec_module(mod.sys)
    mod_os_spec = importlib.util.find_spec('os')
    mod.os = importlib.util.module_from_spec(mod_os_spec)
    mod_os_spec.loader.exec_module(mod.os)
    mod.pyenv = py_env


    mod.sys.stdin = self.stdin_reader
    mod.sys.stdout = self.stdout_writer
    mod.sys.stderr = self.stderr_writer

    mod.sys.argv = argv
    for k, v in environ.items():
      mod.os.environ[k] = v

    return mod, code


  def code_exec(self, mod, code):
    try:
      exec(code, mod.__dict__)
    except Exception:
      traceback.print_exc(file=self.stderr_writer)


  def for_load_code_by_path(self, m : py_env.protocol.LoadCodeByPath):
    file_content = open(m.path, encoding='utf-8').read()
    log("load_code %s" % (m,))
    mod, code = self.get_code(content=file_content,
                              filename=m.path,
                              argv=m.argv,
                              environ=m.environ,
                              pwd=m.pwd)

    self.host_task_queue.put(lambda: self.code_exec(mod, code))
    self.host_task_queue.put(self.task_done)

  def for_load_code(self, m : py_env.protocol.LoadCode):
    mod, code = self.get_code(content=m.code,
                              filename="<anonymous-client-code>",
                              argv=m.argv,
                              environ=m.environ,
                              pwd=m.pwd)

    self.host_task_queue.put(lambda: self.code_exec(mod, code))
    self.host_task_queue.put(self.task_done)

  def read_handler_excetion(self, e : Exception):
    self.stderr_writer.write("Error from pyenv.host: \n")
    traceback.print_exc(file=self.stderr_writer)
    self.host_task_queue.put(self.task_done)

  def task_done(self):
    self.out_queue.put(Message(True, "stdout", ""))
    self.out_queue.put(Message(True, "stderr", ""))
    self.out_queue.put(TaskDone())
    raise StopIteration()

def main(argv):
  parser = argparse.ArgumentParser(add_help=True)
  parser.add_argument('-ip', action='store', dest='ip', default='127.0.0.1', help='IP address of the pyenv host. ')
  parser.add_argument('-port', action='store', default='8964', help='Port of the pyenv host. ', type=int)
  argv = parser.parse_args(argv[1:])

  listen_sock = socket.socket()
  listen_sock.bind((argv.ip, argv.port))
  listen_sock.listen()
  while True:
    try:
      client_sock, client_addr = listen_sock.accept()
      host = Host(client_sock, client_addr)
      host.run()
    except Exception:
      log(file=old_stderr)


if __name__ == '__main__':
  main(sys.argv)