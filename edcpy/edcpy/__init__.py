try:
    import os

    import coloredlogs

    coloredlogs.install(level=os.getenv("LOG_LEVEL", "DEBUG"))
except ImportError:
    pass
