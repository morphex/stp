# Simple developer tools

import sys

DEBUG = True

def DEBUG_PRINT(*arguments):
    if DEBUG:
        print(*arguments, file=sys.stderr)

