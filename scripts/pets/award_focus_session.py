import os
import subprocess
import sys


def main() -> None:
    subprocess.check_call(
        [sys.executable, "scripts/pets/award_xp.py", "75", "Focus session complete", "make_calm"],
        env=os.environ,
    )


if __name__ == "__main__":
    main()
