from os import path
from setuptools import setup, find_packages

# Get the long description from the README file
here = path.abspath( path.dirname( __file__ ) )
with open( path.join( here, 'DESCRIPTION.rst' ), encoding='utf-8' ) as f:
    long_description = f.read()

setup( 
    name='mrcrowbar',
    version='0.5.0',
    description=('A library and model framework for '
                'reverse engineering binary file formats'),
    long_description=long_description,
    url='https://bitbucket.org/moralrecordings/mrcrowbar',
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    python_requires='>=3',
    install_requires=[],
    extras_require={
        'images': ['Pillow >= 2.8.1'],
        'audio': ['pyaudio >= 0.2.9'],
    },
    packages=find_packages( exclude=['doc'] ),
    entry_points={
        'console_scripts': [
            'mrcdiff = mrcrowbar.cli:mrcdiff',
            'mrcdump = mrcrowbar.cli:mrcdump',
        ],
    },
)
