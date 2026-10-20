"""Make the service's own modules importable (`from models import ...`) however pytest is started."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
