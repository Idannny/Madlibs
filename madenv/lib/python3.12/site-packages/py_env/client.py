import py_env
import os

from typing import *
import queue
import socket
import threading
import sys
import argparse
import selectors

from py_env.utils import log

class Client:

  def __init__(self, host_addr : Tuple[str, int], code_config : 'CodeConfig'):
    self.sock = socket.socket()
    self.sock.connect(host_addr)
    self.sock.setblocking(False)

    self.stdin_queue = queue.Queue()
    self.stdout_queue = queue.Queue()
    self.stderr_queue = queue.Queue()

    self.stdin_proxy = py_env.proxy_io.IOProxy(input_queue=None, output_queue=self.stdin_queue)
    self.stdout_proxy = py_env.proxy_io.IOProxy(input_queue=self.stdout_queue, output_queue=None)
    self.stderr_proxy = py_env.proxy_io.IOProxy(input_queue=self.stderr_queue, output_queue=None)

    self.command_handlers = {
      py_env.protocol.TaskDone: self.for_task_done
    }

    self.socket_splitter = py_env.proxy_io.SocketSplitter(protocol=py_env.protocol.JsonProtocol(),
                                                          sock=self.sock,
                                                          sock_write_source=self.stdin_queue,
                                                          sock_stdin_dest=None,
                                                          sock_stdout_dest=self.stdout_queue,
                                                          sock_stderr_dest=self.stderr_queue,
                                                          command_handlers=self.command_handlers,
                                                          on_broken_pipe=self.done)
    self.running = True
    
    self.code_config = code_config

  def stdin_collector(self):
    selector = selectors.DefaultSelector()
    selector.register(sys.stdin.fileno(), selectors.EVENT_READ)
    while self.running:
      r = selector.select(timeout=0.01)
      if len(r) > 0:
        _in = sys.stdin.readline()
        self.stdin_proxy.write("stdin", _in)

  def stdout_collector(self):
    try:
      while not self.stdout_proxy.empty():
        print(self.stdout_proxy.read(), end='')
    except EOFError:
      pass

  def stderr_collector(self):
    try:
      while not self.stderr_proxy.empty():
        print(self.stderr_proxy.read(), end='', file=sys.stderr)
    except EOFError:
      pass
      
  def load_code(self, cfg : 'CodeConfig'):
    if cfg.code == None:
      obj = py_env.protocol.LoadCodeByPath(
        path=cfg.code_path,
        pwd=cfg.pwd,
        environ=cfg.environ,
        argv=cfg.argv
      )
    else:
      obj = py_env.protocol.LoadCode(
        code=cfg.code,
        pwd=cfg.pwd,
        environ=cfg.environ,
        argv=cfg.argv
      )
    
    self.stdin_queue.put(obj)    

  def run(self):
    threading.Thread(target=self.socket_splitter.run).start()
    threading.Thread(target=self.stdin_collector).start()
    threading.Thread(target=self.stdout_collector).start()
    threading.Thread(target=self.stderr_collector).start()
    
    self.load_code(self.code_config)

  def done(self):
    self.socket_splitter.done = True
    self.running = False

  def for_task_done(self, obj : py_env.protocol.TaskDone):
    self.done()


class CodeConfig:
  
  def __init__(self, code_path, pwd=None, environ=None, argv=None, code=None):
    self.code_path = code_path
    self.pwd = os.getcwd() if pwd is None else pwd
    self.environ = dict(os.environ)
    if environ:
      self.environ.update(environ)
    self.argv = [code_path] if argv is None else argv
    self.code = code

def main(argv):
  parser = argparse.ArgumentParser(add_help=True)
  path_arg = parser.add_argument_group('required named arguments')
  path_arg.add_argument('-f', action='store', default=None, help='The path to your code. ')
  optionals = parser.add_argument_group('required named arguments')
  optionals.add_argument('-ip', action='store', dest='ip', default='127.0.0.1', help='IP address of the pyenv host. ')
  optionals.add_argument('-port', action='store', default='8964', help='Port of the pyenv host. ', type=int)
  optionals.add_argument('-wd', action='store', default=os.getcwd(), help='The user working directory. '
                                                                          'The host will switch to the directory to find `f`, '
                                                                          'and execute your code. ')
  optionals.add_argument('-env', action='store', default=None, help='Extra environment variables for your script. ')
  optionals.add_argument('-c', action='store', default=None, help='Python script, executed with pyenv imported. '
                                                                  'This will override `f` argument. ')

  optionals.add_argument('rest', nargs=argparse.REMAINDER)
  argv = parser.parse_args(argv[1:])

  client = Client((argv.ip, argv.port),
                  CodeConfig(argv.f, pwd=argv.wd, environ=argv.env, argv=[argv.f] + argv.rest, code=argv.c))
  client.run()

if __name__ == '__main__':
  main(sys.argv)