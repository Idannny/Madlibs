import sys

old_stdout = sys.stdout
old_stderr = sys.stderr
old_stdin = sys.stdin

def log(*args, **kwargs):
  print(*args, file=old_stderr)