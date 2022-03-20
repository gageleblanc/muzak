import setuptools
import muzak

# with open("readme.md", "r") as fh:
#     long_description = fh.read()

setuptools.setup(
    name='muzak',
    version=muzak.__version__,
    scripts=[],
    entry_points={
        'console_scripts': ["muzak = muzak.cli.__main__:cli"]
    },
    author="Gage LeBlanc",
    author_email="gleblanc@symnet.io",
    description="A library organizing music",
    long_description="long_description",
    long_description_content_type="text/markdown",
    url="https://github.com/gageleblanc/muzak",
    packages=setuptools.find_packages(),
    install_requires=['clilib>=3.5.1', 'pytaglib>=1.5.0', 'tabulate'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
