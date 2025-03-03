import io
import socket
import queue
import selectors
import logging
import threading
from py_env.protocol import JsonProtocol, Message, TaskDone
from py_env.utils import log

class SocketSplitter:

  def __init__(self, protocol : JsonProtocol,
               sock : socket.socket,
               command_handlers : dict = None,
               sock_write_source : queue.Queue = None,
               sock_stdin_dest : queue.Queue = None,
               sock_stdout_dest : queue.Queue = None,
               sock_stderr_dest : queue.Queue = None,
               on_broken_pipe = None,
               on_read_handler_exception = None):
    self.protocol = protocol
    self.sock = sock
    self.done = False
    self.command_handlers = command_handlers
    self.sock_write_source = sock_write_source
    self.sock_stdin_dest = sock_stdin_dest
    self.sock_stdout_dest = sock_stdout_dest
    self.sock_stderr_dest = sock_stderr_dest
    self.on_broken_pipe = on_broken_pipe
    self.on_read_handler_exception = on_read_handler_exception

  def sock_reader(self):
    buffer = bytearray()
    while True:
      new_data = yield
      new_data : bytes
      for b in new_data:
        buffer.append(b)
        if b == self.protocol.sep:
          self.read_handler(buffer)
          buffer = bytearray()

  def sock_writer(self):
    while True:
      try:
        head = self.sock_write_source.get_nowait()
        encoded = self.protocol.encode(head)
        while len(encoded) > 0:
          sent = self.sock.send(encoded)
          yield
          encoded = encoded[sent:]
        if isinstance(head, TaskDone):
          self.done = True
          self.sock.close()
      except queue.Empty:
        yield

  # TODO: read_handler should be client/host specific
  def read_handler(self, buffer : bytearray):
    try:
      decoded = self.protocol.decode(buffer)
      def for_message(obj : Message):
        {
          "stdin": self.sock_stdin_dest,
          "stdout": self.sock_stdout_dest,
          "stderr": self.sock_stderr_dest
        }[obj.tunnel].put(obj)

      basic_handlers = {
        Message: for_message
      }

      if type(decoded) in basic_handlers:
        basic_handlers[type(decoded)](decoded)
      elif self.command_handlers and type(decoded) in self.command_handlers:
        self.command_handlers[type(decoded)](decoded)
      else:
        raise ValueError("Unhandled message %r" % decoded)

    except Exception as e:
      log(e)
      if self.on_read_handler_exception:
        self.on_read_handler_exception(e)


  def run(self):
    selector = selectors.DefaultSelector()
    sock_reader = self.sock_reader()
    sock_reader.send(None)
    sock_writer = self.sock_writer()
    sock_writer.send(None)
    selector.register(self.sock.fileno(), events=selectors.EVENT_WRITE | selectors.EVENT_READ)
    try:
      while self.done == False:
        results = selector.select()
        for event_key, event_mask in results:
          if event_mask & selectors.EVENT_READ != 0:
            sock_reader.send(self.sock.recv(4096))
          if event_mask & selectors.EVENT_WRITE != 0:
            sock_writer.send(None)
    except BrokenPipeError:
      log("broken pipe")
      if self.on_broken_pipe:
        self.on_broken_pipe()


class StringBuffer:

  def __init__(self):
    self._buffer = []
    self._buffer_size = 0
    self.lock = threading.Lock()
    self.eof = False

  def read_until_from_queue(self, n, q : queue.Queue, cond : callable = None):

    while n < 0 or self._buffer_size < n:
      if cond is None:
        try:
          message: Message = q.get_nowait()
        except queue.Empty:
          break
      else:
        message: Message = q.get()

      if message.eof:
        self.eof = True
        if self._buffer_size == 0:
          raise EOFError
        break

      self._buffer.append(message.message)
      self._buffer_size += len(message.message)
      if cond and cond(message):
        break

  def readline_from_queue(self, q):
    with self.lock:
      self.read_until_from_queue(-1, q, lambda x : "\n" in x.message)

      result = ''
      while len(self._buffer) != 0:
        newline_index = self._buffer[0].find('\n')
        if newline_index == -1:
          result += self._buffer[0]
          self._buffer_size -= len(self._buffer[0])
          self._buffer.pop(0)
        else:
          result += self._buffer[0][0:newline_index + 1]
          if newline_index == len(self._buffer[0]) - 1:
            self._buffer.pop(0)
          else:
            self._buffer[0] = self._buffer[0][newline_index + 1:]
          self._buffer_size -= newline_index + 1
          break
      return result

  def read_from_queue(self, q, n=-1):
    with self.lock:
      self.read_until_from_queue(n, q)

      if n < 0:
        result = ''.join(self._buffer)
        self._buffer = []
        self._buffer_size = 0
      else:
        result = ''
        rest = n
        while len(self._buffer) != 0 and rest > 0:
          l = len(self._buffer[0])
          if l <= rest:
            result += self._buffer[0]
            self._buffer.pop(0)
            self._buffer_size -= l
            rest -= l
          else:
            result += self._buffer[0][0:rest]
            self._buffer[0] = self._buffer[0][rest:]
            self._buffer_size -= rest
            rest -= rest

      return result


class IOProxy:

  def __init__(self,
               input_queue : queue.Queue = None,
               output_queue : queue.Queue = None):
    self.input_queue = input_queue
    self.output_queue = output_queue

    self._buffer = StringBuffer()

  def read(self, n=-1):
    return self._buffer.read_from_queue(self.input_queue, n)

  def readline(self):
    return self._buffer.readline_from_queue(self.input_queue)

  def write(self, tunnel : str, text : str):
    self.output_queue.put(Message(eof=False, tunnel=tunnel, message=text))

  def empty(self):
    return self._buffer.eof == True

class IOProxyReader:

  def __init__(self, proxy : IOProxy, *args, **kwargs):
    self._proxy = proxy

  def read(self, n=-1):
    return self._proxy.read(n)

  def readline(self, *args, **kwargs):
    return self._proxy.readline()

  def flush(self):
    pass

  def empty(self):
    return self._proxy.empty()


class IOProxyWriter:

  def __init__(self, tunnel : str, proxy : IOProxy, *args, **kwargs):
    self.tunnel = tunnel
    self._proxy = proxy

  def write(self, t : str):
    self._proxy.write(self.tunnel, t)

  def flush(self):
    pass


