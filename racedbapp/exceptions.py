class ResultImportError(Exception):
    """Raised when results data is invalid and cannot be imported.

    The message is user-facing: it should describe what was wrong so
    whoever submitted the sheet can fix it.
    """
