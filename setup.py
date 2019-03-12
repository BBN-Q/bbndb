from setuptools import setup

setup(
    name='bbndb',
    version='0.1.0',
    author='Graham Rowlands',
    scripts=[],
    packages=['bbndb'],
    description='BBN Configuration Database',
    long_description=open('README.md').read(),
    install_requires=[
		"sqlalchemy >= 1.2.15",
		"numpy >= 1.11.1",
		"networkx >= 1.11"
    ]
)
