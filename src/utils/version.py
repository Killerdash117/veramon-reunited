"""
Version information for Veramon Reunited.

This module contains version information and provides utilities
for version checking and compatibility testing.
"""

# Version follows format: major.minor.patch
VERSION = "0.32.001"
VERSION_NAME = "Security Update"
VERSION_DATE = "April 19, 2025"
VERSION_STATUS = "In Development"

# Current API version for external integrations
API_VERSION = "1.0"

def get_version():
    """Returns the current version as a string."""
    return VERSION

def get_version_info():
    """Returns complete version information as a dictionary."""
    return {
        "version": VERSION,
        "name": VERSION_NAME,
        "date": VERSION_DATE,
        "status": VERSION_STATUS,
        "api_version": API_VERSION
    }

def print_version_info():
    """Prints version information in a formatted way."""
    print(f"Veramon Reunited v{VERSION} - {VERSION_NAME}")
    print(f"Released: {VERSION_DATE}")
    print(f"Status: {VERSION_STATUS}")
    print(f"API Version: {API_VERSION}")
