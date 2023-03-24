from setuptools import find_packages, setup

setup(
    name="pixoo_api",
    packages=find_packages(include=["pixoo_api"]),
    version="0.0.1",
    description="A Python library for the Divoom Pixoo 64",
    author="David Gray",
    license="MIT",
    install_requires=["requests"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    test_suite="tests",
)
