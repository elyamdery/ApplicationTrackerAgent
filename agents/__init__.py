"""
Agents package initialization.
This file makes Python treat the directory as a package.
"""

from .email_monitor import EmailMonitorAgent

__all__ = ['EmailMonitorAgent']