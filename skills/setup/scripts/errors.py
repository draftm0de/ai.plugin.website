"""Exit codes and the exception used for every controlled stop."""

EXIT_OK = 0
EXIT_STOP = 1   # precondition failed: print "STOP: ..." and end
EXIT_ASK = 2    # input missing: print "ASK: ..." and let the caller ask the user


class Stop(Exception):
    """A precondition failed. The message says what to do."""


class Ask(Exception):
    """An input is missing. The message is the question for the user."""
