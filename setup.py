"""
Setup script for Civitai Sync
"""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent

# Read requirements
requirements = []
if (this_directory / "requirements.txt").exists():
    requirements = (this_directory / "requirements.txt").read_text().strip().split('\n')

setup(
    name="civitai-sync",
    version="0.0.6",
    author="Ventexx",
    description="Sync safetensor model metadata and images from Civitai",
    packages=find_packages(),
    py_modules=['main'],
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'civitai-sync=main:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Attribution-NonCommercial 4.0 International",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
)