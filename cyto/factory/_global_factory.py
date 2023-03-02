from ._arg_factory_group import ArgFactoryGroup

# The default `ArgFactoryGroup` instance that we register our various
# factory functions with.
# TODO: Replace `ArgFactoryGroup` with something more generic. E.g., something
# that doesn't take `inspect.Parameter` as input. In turn, rework `ArgFactoryGroup`
# on top of that generic implementation.
FACTORY = ArgFactoryGroup()
