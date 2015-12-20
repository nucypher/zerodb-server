from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'ipython',
    'zerodb']

setup(
    name="zerodb-server",
    version="0.1",
    description="ZeroDB server",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="AGPLv3",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
    entry_points={
        "console_scripts": [
            "zerodb-server = zerodb.server.run:run",
            "zerodb-manage = zerodb.server.manage:cli"
            ]
        }
)
