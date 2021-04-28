from os import path
from setuptools import setup, find_packages
from mrcrowbar.version import __version__

# Get the long description from the README file
here = path.abspath( path.dirname( __file__ ) )
with open( path.join( here, 'DESCRIPTION.rst' ), encoding='utf-8' ) as f:
    long_description = f.read()

setup( 
    name='mrcrowbar',
    version=__version__,
    description=('A library and model framework for '
                'reverse engineering binary file formats'),
    long_description=long_description,
    url='https://moral.net.au/mrcrowbar',
    license='BSD',
    author='Scott Percival',
    author_email='code@moral.net.au',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires='>=3',
    install_requires=[],
    extras_require={
        'images': ['Pillow >= 2.8.1'],
        'audio': ['miniaudio >= 1.41'],
    },
    packages=find_packages( exclude=['doc'] ),
    entry_points={
        'console_scripts': [
            'mrcdiff = mrcrowbar.cli:mrcdiff',
            'mrcdump = mrcrowbar.cli:mrcdump',
            'mrchist = mrcrowbar.cli:mrchist',
            'mrcpix = mrcrowbar.cli:mrcpix',
            'mrcgrep = mrcrowbar.cli:mrcgrep',
            'mrcfind = mrcrowbar.cli:mrcfind',
        ],
    },
)
