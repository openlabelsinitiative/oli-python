from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="oli-python",
    version="2.0.7",
    author="Lorenz Lehmann",
    author_email="lorenz@growthepie.com",
    description="Python SDK for interacting with the Open Labels Initiative; A standard, registry and trust layer for EVM address labels.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openlabelsinitiative/oli-python",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.9',
    install_requires=[
        'web3>=6.0.0',
        'PyYAML>=6.0.0',
        'networkx>=3.4.2'
    ]
)