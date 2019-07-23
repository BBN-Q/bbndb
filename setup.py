from setuptools import setup

setup(
    name='bbndb',
    version='2019.1',
    author='Graham Rowlands',
    scripts=[],
    packages=['bbndb'],
    url='https://github.com/BBN-Q/bbndb',
    download_url='https://github.com/BBN-Q/bbndb',
    license="Apache 2.0 License",
    description='BBN Configuration Database',
    long_description_content_type='text/markdown',
    long_description=open('README.md').read(),
    install_requires=[
		"sqlalchemy >= 1.2.15",
		"numpy >= 1.12.1",
		"networkx >= 1.11",
        "IPython"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering",
    ],
    python_requires='>=3.6',
    keywords="quantum qubit instrument experiment control database configuration"
)

# python setup.py sdist
# python setup.py bdist_wheel
# For testing:
# twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# For distribution:
# twine upload dist/*
# Test with:
# pip install --extra-index-url https://test.pypi.org/simple/ bbndb

# conda skeleton pypi --pypi-url https://test.pypi.io/pypi/