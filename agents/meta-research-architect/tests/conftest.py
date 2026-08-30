import os
import sys

# The agent uses flat imports (`import config`); put its root on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
