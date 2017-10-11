from setuptools import setup, find_packages

setup(name='mrcrowbar',
    version='0.4.0',
    description=('A library and model framework for '
                'reverse engineering binary file formats'),
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
    install_requires=[
        'Pillow>=2.8.1',
        'pyaudio>=0.2.9',
    ],
    packages=find_packages(exclude=['doc']))
