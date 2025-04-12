from setuptools import setup

setup(
    name="test-package",
    version="0.1.0",
    description="Test package for integration tests",
    author="Test Author",
    author_email="test@example.com",
    py_modules=["test_module"],
    install_requires=["pyfluent-iterables>=2.0.0"],
)
