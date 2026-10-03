class WorkspaceUnavailable(Exception):
    """A workspace dependency is unavailable; do not expose its internal error."""


class ProjectNotFound(Exception):
    """Missing and inaccessible projects use the same response."""
