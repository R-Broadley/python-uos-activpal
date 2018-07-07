"""Setup for package uos_activpal."""

import setuptools
import uos_activpal.__init__ as specs


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=specs.name,
    version=specs.version,
    description='A package for working with activPAL data',
    author='Rob Broadley',
    author_email='software@rbroadley.co.uk',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='GPLv2',
    url='https://github.com/R-Broadley/python-uos-activpal',
    download_url='https://github.com/R-Broadley/python-uos-activpal/archive/{ver}.tar.gz'.\
        format(ver=specs.version),
    packages=setuptools.find_packages(),
    include_package_data=True,
    keywords=['activpal', 'accelerometer', 'wearable', 'activity-monitor'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        ),
    )
