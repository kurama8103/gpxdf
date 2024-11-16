#!/usr/bin/env python3
# coding: utf-8
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gpxdf",  # Replace with your own username
    version="1.0.1",
    author="kurama8103",
    # author_email="author@example.com",
    description="gpx file to pandas dateframe",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kurama8103/gpxdf",
    packages=setuptools.find_packages(),
    install_requires=["pandas", "gpxpy", "geopy", "folium", "fitparse"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
