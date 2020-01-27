import pkg_resources

from side_effects import __version__


def test_version():
    """Check the pyproject.toml and __version__ match."""
    my_version = pkg_resources.get_distribution('side_effects').version
    assert my_version == __version__
