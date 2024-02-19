from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pydatalab")
except PackageNotFoundError:
    __version__ = "develop"
