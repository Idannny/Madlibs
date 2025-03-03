import json
from typing import *

class Message(NamedTuple):
  eof : bool
  tunnel : str
  message : str

  def encode(self):
    return JsonProtocol.obj_to_bytes({
      "method": "msg",
      "tunnel": self.tunnel,
      "message": self.message,
      "eof": self.eof
    })


class LoadCodeByPath(NamedTuple):
  path : str
  pwd : str
  environ : dict
  argv : list

  def encode(self):
    return JsonProtocol.obj_to_bytes({
      "method": "load_code_by_path",
      "path": self.path,
      "pwd": self.pwd,
      "environ": self.environ,
      "argv": self.argv
    })

class LoadCode(NamedTuple):
  code : str
  pwd : str
  environ : dict
  argv : list

  def encode(self):
    return JsonProtocol.obj_to_bytes({
      "method": "load_code",
      "code": self.code,
      "pwd": self.pwd,
      "environ": self.environ,
      "argv": self.argv
    })

class TaskDone(NamedTuple):
  def encode(self):
    return JsonProtocol.obj_to_bytes({
      "method": "task_done"
    })

class JsonProtocol:

  sep = ord('\n')

  @staticmethod
  def obj_to_bytes(obj : dict):
    return json.dumps(obj, ensure_ascii=False).encode('utf-8') + b'\n'

  @staticmethod
  def bytes_to_obj(b : bytes) -> dict:
    return json.loads(b.decode('utf-8'), encoding='utf-8')

  @staticmethod
  def encode(obj) -> bytes:
    return obj.encode()

  @staticmethod
  def decode(b: bytes):
    try:
      d = JsonProtocol.bytes_to_obj(b)

      # if d["method"] == "msg":
      #   return Message(tunnel=d["tunnel"], message=d["message"], eof=d["eof"])
      # elif d["method"] == "load_code_by_path":
      #   return LoadCodeByPath(path=d["path"], pwd=d["pwd"], environ=d["environ"], argv=d["argv"])
      # elif d["method"] == "task_done":
      #   return TaskDone()
      #
      # else:
      #   raise ValueError()
      return {
        "msg": lambda: Message(tunnel=d["tunnel"], message=d["message"], eof=d["eof"]),
        "load_code_by_path": lambda: LoadCodeByPath(path=d["path"], pwd=d["pwd"], environ=d["environ"], argv=d["argv"]),
        "load_code": lambda: LoadCode(code=d["code"], pwd=d["pwd"], environ=d["environ"], argv=d["argv"]),
        "task_done": lambda: TaskDone(),
      }[d["method"]]()

    except Exception as e:
      raise ValueError("Wrong message: %r" % b)