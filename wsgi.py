#!/usr/bin/env python3
"""
WSGI entry point for the AI Finance Management System
"""

import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import app

if __name__ == "__main__":
    app.run()

