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
		# "pony >= 0.7.4", # This needs to be 0.7.4-dev
		"numpy >= 1.11.1",
		"networkx >= 1.11"
    ]
)
