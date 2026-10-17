class ResultImportError(Exception):
    """Raised when results data is invalid and cannot be imported.

    The message is user-facing: it should describe what was wrong so
    whoever submitted the sheet can fix it.
    """

    # True when individual results were saved before the error, so the
    # overall import is a partial success rather than a total failure.
    partial = False
