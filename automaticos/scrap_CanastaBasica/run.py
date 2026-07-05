import os
import sys

# Add the directory containing main.py to sys.path to ensure relative imports resolve correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from main import main

if __name__ == "__main__":
    main()
