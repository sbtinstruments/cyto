import inspect


def frames_to_log_message(frames: list[inspect.FrameInfo] | None = None) -> str:
    """Return log message based on the context."""
    if frames is None:
        frames = inspect.stack(context=0)
    try:
        # We usually call `frames_to_log_message` within a function like:
        #
        #     @contextmanager
        #     def log_duration(...):
        #         ...
        #
        # Note that:
        #
        #  * Frame 0: Is for `frames_to_log_message` itself
        #  * Frame 1: Is for `log_duration` itself
        #  * Frame 2: Is for `@contextmanager`
        #  * Frame 3: Is the actual "caller" (where the `with log_duration`
        #    statement is)
        #
        parent_frame = frames[3]
    except IndexError:
        return ""
    func_name = parent_frame.function
    func_line = parent_frame.lineno
    return f"Code block (starting at line {func_line}) in {func_name}"
