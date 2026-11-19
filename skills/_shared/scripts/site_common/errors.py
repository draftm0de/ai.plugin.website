"""Exit codes and the exceptions used for every controlled stop."""

EXIT_OK = 0
EXIT_STOP = 1   # precondition failed: print "STOP: ..." and end
EXIT_ASK = 2    # input missing or ambiguous: ask the user


class Stop(Exception):
    """A precondition failed. The message says what to do."""


class Ask(Exception):
    """Input is missing or ambiguous. The message is the question; options are attached."""

    def __init__(self, message, options=None):
        super().__init__(message)
        self.options = options or []
