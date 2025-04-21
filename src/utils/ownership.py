"""
OWNERSHIP AND COPYRIGHT NOTICE

This file is part of Veramon Reunited, a Discord bot created by killerdash117.
Copyright © 2025 killerdash117. All rights reserved.

GitHub: https://github.com/killerdash117
Project: https://github.com/killerdash117/veramon-reunited

This code is protected by copyright law. Unauthorized reproduction or
distribution of any part of this software may result in legal action.

License: MIT (see LICENSE file for details)
"""

# This module provides utility functions related to ownership verification
# It can be imported by other modules that need to check ownership status

import os
import sys
from typing import Dict, List, Optional

# Ownership information
OWNER = "killerdash117"
GITHUB = "https://github.com/killerdash117"
COPYRIGHT_YEAR = "2025"
PROJECT = "Veramon Reunited"

def get_ownership_info() -> Dict[str, str]:
    """
    Returns the ownership information for the project.
    
    Returns:
        Dict containing owner name, GitHub username, copyright year, and project name
    """
    return {
        "owner": OWNER,
        "github": GITHUB,
        "year": COPYRIGHT_YEAR,
        "project": PROJECT
    }

def verify_ownership() -> bool:
    """
    Verifies the ownership of the code by checking if the ownership files exist.
    
    Returns:
        True if ownership is verified, False otherwise
    """
    # Check for ownership file
    expected_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "OWNERSHIP.md")
    return os.path.exists(expected_path)

def get_ownership_notice() -> str:
    """
    Returns a standardized ownership notice string.
    
    Returns:
        String containing the ownership notice
    """
    return f"© {COPYRIGHT_YEAR} {OWNER} | {PROJECT} | {GITHUB}"
