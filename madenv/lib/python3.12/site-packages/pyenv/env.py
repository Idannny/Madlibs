_env = {}

def set(k, v):
  _env[k] = v

def get(k):
  return _env[k]

def keys():
  return _env.keys()