"""Make the skill's bundled Python dependencies importable.

Import this module for its side effect before importing ``requests`` or
``bs4``. It adds the vendored pure-Python packages under ``_vendor/`` —
``requests``, ``beautifulsoup4`` and their dependencies — to ``sys.path``
so the audit scripts run with no ``pip install`` step.

A system-installed copy, if present, still wins: ``_vendor`` is appended
after the existing path rather than inserted ahead of it, so we only fill
the gap when the package is missing.
"""

import os
import sys

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")
if os.path.isdir(_VENDOR) and _VENDOR not in sys.path:
    sys.path.append(_VENDOR)
