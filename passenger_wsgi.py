import os
import sys

# Flask uygulamamızın yolu
INTERP = os.path.expanduser("/home/auronfy1/idm.auronfy.com/venv/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from app import app as application 