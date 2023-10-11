from setuptools import setup, find_packages

description = 'A tool for multi-modal traffic network analyzis'

setup(
    name='Mobility Referential',
    version='1.0.0',
    license='GPL',
    description=description,
    author='Matthieu Mastio',
    url='https://github.com/odyssee-co/mobility-referential',
    packages=["mobref"],
    install_requires=[
        'geopandas>=0.10.2',
        'matplotlib>=3.1.2',
        'numpy>=1.17.4',
        'osmium>=3.6.0',
        'osmnx>=1.4.0',
        'pandana>=0.6.1',
        'pandas==1.5.3',
        'pyvroom>=1.13.2',
        'PyYAML>=6.0.1',
        'Shapely>=1.7.0',
        'urbanaccess>=0.2.2',
        'vroom>=1.0.2',
        'pyarrow>=12.0.1'
    ]
)
