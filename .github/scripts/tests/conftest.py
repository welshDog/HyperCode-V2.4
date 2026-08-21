import os
import sys

# Make fleet_registry.py (one directory up) importable from this tests/
# directory — pytest does not do this automatically, same reason
# agents/fleet-controller/tests/conftest.py needs the equivalent line.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
