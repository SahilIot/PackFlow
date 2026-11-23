# Exceptions shared by the data layer and the UI. The UI shows str(exc) to the user, so messages are written for people.
from __future__ import annotations

class DatabaseError(Exception):
    """Any failure to read or save data on this computer. The message is safe to show """
