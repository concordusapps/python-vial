# -*- coding: utf-8 -*-
import sys
from .meta import version as __version__, description
from .session import Session

# Set the package docstring to the metadata description.
sys.modules[__package__].__doc__ = description

# Expose named attributes.
__all__ = [
    'Session'
]
