import sys
import os

# Add project root to path so backend/main.py can be imported
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, 'backend'))
sys.path.insert(0, root)

from main import app

handler = app
