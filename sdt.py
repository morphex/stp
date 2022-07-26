# Simple developer tools

import sys

DEBUG = True
INFO = False

def DEBUG_PRINT(*arguments, DEBUG=DEBUG):
    if DEBUG:
        print(*arguments, file=sys.stderr)

def INFO_PRINT(*arguments, INFO=INFO):
    if INFO:
        print(*arguments, file=sys.stderr)

