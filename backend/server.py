"""
Backend server wrapper for supervisor compatibility.
Imports the main app from parent directory.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Export the app for uvicorn
__all__ = ["app"]
