from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'ipython>=1.0.0',
    'click',
    'zerodb>=0.99.0a2',
    'PyOpenSSL',
    'ecdsa'
]

setup(
    name="zerodb-server",
    version="0.2.0a2",
    description="ZeroDB server",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="AGPLv3",
    url="http://zerodb.io",
    packages=find_packages(),
    namespace_packages=["zerodbext"],
    install_requires=INSTALL_REQUIRES,
    entry_points={
        "console_scripts":
        [
            "zerodb-server = zerodbext.server.run:run",
            "zerodb-manage = zerodbext.server.manage:cli",
            # "zerodb-api = zerodbext.server.api:run"
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha"
        ]
)
