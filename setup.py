import os

from setuptools import setup

VERSION = "0.3"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="todoist-to-sqlite",
    description="Save data from Todoist to a SQLite database",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Benjamin Congdon",
    author_email="me@bcon.gdn",
    maintainer="Nick Loadholtes",
    maintainer_email="nick@ironboundsoftware.com",
    url="https://github.com/nloadholtes/todoist-to-sqlite",
    project_urls={
        "Source": "https://github.com/nloadholtes/todoist-to-sqlite",
        "Issues": "https://github.com/nloadholtes/todoist-to-sqlite/issues",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
    ],
    keywords="todoist sqlite export dogsheep",
    version=VERSION,
    packages=["todoist_to_sqlite"],
    entry_points="""
        [console_scripts]
        todoist-to-sqlite=todoist_to_sqlite.cli:cli
    """,
    install_requires=[
        "click",
        "sqlite-utils~=3.1",
        "tqdm~=4.36",
    ],
    extras_require={"test": ["pytest"]},
    tests_require=["todoist-to-sqlite[test]"],
)
