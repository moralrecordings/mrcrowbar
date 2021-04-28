Mr. Crowbar
###########
|pypi| |tests| |coverage|

.. |pypi|     image:: https://img.shields.io/pypi/v/mrcrowbar.svg
              :target: https://pypi.org/project/mrcrowbar
.. |tests|    image:: https://github.com/moralrecordings/mrcrowbar/actions/workflows/main.yml/badge.svg
              :target: https://github.com/moralrecordings/mrcrowbar/actions
.. |coverage| image:: https://coveralls.io/repos/github/moralrecordings/mrcrowbar/badge.svg?branch=master
              :target: https://coveralls.io/github/moralrecordings/mrcrowbar?branch=master

.. image:: doc/source/_static/mrcrowbar.png

Wait, what?!
============

Mr. Crowbar is a Django-esque model framework that makes it super easy to work with proprietary binary formats while reverse engineering. 

File formats are described with Python classes that allow ORM-like free modification of structures and properties, which in turn can be validated and converted back to the binary equivalent at any time.

The eventual goal is to provide a library for storing file format information that retains the readability of a text file, while providing instant read/write support for almost no cost.


Getting started
===============

Mr. Crowbar is written in Python 3. You can install the latest point release of the library from the Python Package Index:

.. code:: bash

   pip3 install mrcrowbar

For development, you can `create a virtualenv for Python 3 <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_ and load this directory in as a package:

.. code:: bash
   
    git clone https://github.com/moralrecordings/mrcrowbar
    cd mrcrowbar
    virtualenv -p /usr/bin/python3 venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -e .
    pip install ipython     # for a nicer Python shell with autocomplete

Windows 10 users: I highly recommend installing the `Windows Subsystem for Linux <https://docs.microsoft.com/en-us/windows/wsl/install-win10>`_ and using Ubuntu's bundled Python installation, instead of the native Win32 console edition.

[This chunk of the README needs a lot of work. If you are struggling, please hit me up via `email <mailto:code@moral.net.au>`_ or on Twitter at `@moralrecordings <https://twitter.com/moralrecordings>`_.]


Give us an example
==================

Here's a class for a level file used by the 1991 DOS game *Lemmings*, taken from mrcrowbar.lib.games.lemmings:

.. code:: python

    class Level( mrc.Block ):
        """Represents a single Lemmings level."""

        #: Minimum Lemming release-rate.
        release_rate =      mrc.UInt16_BE( 0x0000, range=range( 0, 251 ) )
        #: Number of Lemmings released.
        num_released =      mrc.UInt16_BE( 0x0002, range=range( 0, 115 ) )
        #: Number of Lemmings required to be saved.
        num_to_save =       mrc.UInt16_BE( 0x0004, range=range( 0, 115 ) )
        #: Time limit for the level (minutes).
        time_limit_mins =   mrc.UInt16_BE( 0x0006, range=range( 0, 256 ) )
        #: Number of skills.
        num_climbers =      mrc.UInt16_BE( 0x0008, range=range( 0, 251 ) )
        num_floaters =      mrc.UInt16_BE( 0x000a, range=range( 0, 251 ) )
        num_bombers =       mrc.UInt16_BE( 0x000c, range=range( 0, 251 ) )
        num_blockers =      mrc.UInt16_BE( 0x000e, range=range( 0, 251 ) )
        num_builders =      mrc.UInt16_BE( 0x0010, range=range( 0, 251 ) )
        num_bashers =       mrc.UInt16_BE( 0x0012, range=range( 0, 251 ) )
        num_miners =        mrc.UInt16_BE( 0x0014, range=range( 0, 251 ) )
        num_diggers =       mrc.UInt16_BE( 0x0016, range=range( 0, 251 ) )
        #: Raw value for the start x position of the camera.
        camera_x_raw =      mrc.UInt16_BE( 0x0018, range=range( 0, 1265 ) )
        
        #: Index denoting which graphical Style to use.
        style_index =       mrc.UInt16_BE( 0x001a )
        #: Index denoting which Special graphic to use (optional).
        custom_index =      mrc.UInt16_BE( 0x001c )

        #: List of Interactive object references (32 slots).
        interactives =      mrc.BlockField( Interactive, 0x0020, count=32, fill=b'\x00' )
        #: List of Terrain object references (400 slots).
        terrains =          mrc.BlockField( Terrain, 0x0120, count=400, fill=b'\xff' )
        #: List of SteelArea object references (32 slots).
        steel_areas =       mrc.BlockField( SteelArea, 0x0760, count=32, fill=b'\x00' )
        #: Name of the level (ASCII string).
        name =              mrc.Bytes( 0x07e0, length=32, default=b'                                ' )

        @property
        def camera_x( self ):
            """Start x position of the camera."""
            return self.camera_x_raw - (self.camera_x_raw % 8)

        @property
        def repr( self ):
            return self.name.strip().decode( 'utf8' )

Binary layouts in Mr. Crowbar are called blocks. To open a binary format, you can create a Python class inheriting from ``Block``, with a number of ``Field`` objects as class variables. Fields are rules for how to interpret bytes in a block. At any time, you can construct a new ``Block`` object from a raw byte string, or generate the byte string equivalent of an existing ``Block`` object.

In the Lemmings level format, all of the numeric variables (e.g. release rate, number of each skill) are stored at the start of the file as unsigned 16-bit big-endian integers. To read these, the ``Level`` class defines a number of ``UInt16_BE`` field objects at the class level. Each ``UInt16_BE`` is created with a (block relative) offset to read data from, and occasionally a ``range`` parameter which constrains it to a list of allowable values. (Adding a ``range`` is an example of an extra validation rule you can add to a field.)

Mr. Crowbar offers fields for all of the common primitive types. There are also special fields that extend the primitives; an example is ``Bits``, which lets you create multiple variables from masked-off bits in the same byte.

Finally, there is the option to load other ``Block`` classes from inside a parent block; ``interactives``, ``terrains`` and ``steel_areas`` are defined using ``BlockField``, which produces lists of ``Interactive``, ``Terrain`` and ``SteelArea`` blocks respectively.

As blocks are Python classes, it is trivial to extend them with custom code; here we've created a ``camera_x`` property which provides a transformed view of ``camera_x_raw`` taking into account the limitations of the game engine. This is useful for e.g. bitpacked values that need mathematical transformation to get the useful real-world equivalent.


That wasn't an example, that was a snoozefest! Just tell me how to hack already 
===============================================================================

Here's some code to edit a Lemmings level. (This will modify your game, so be sure to do this on a copy!)

.. code:: python

    from mrcrowbar.lib.games import lemmings
    from mrcrowbar import utils

    # auto-load all the files
    ll = lemmings.Loader()
    ll.load( '/path/to/copy/of/lemmings' )

    # pick the first level of Tricky
    level = ll['./Level000.dat'].levels[0]   # <Level: This should be a doddle!>

    # Level is a block type, which means we can peek at the bytes representation at any time
    bytes_orig = level.export_data()
    print( 'Original level data:' )
    utils.hexdump( bytes_orig )

    # change some stuff around!
    level.release_rate = 99
    level.num_to_save = 1
    level.name = b'  oh hey I just hacked a level  '

    # now that the block has changed, the bytes will be different
    bytes_new = level.export_data()
    print( 'Changes:' )
    utils.hexdump_diff( bytes_orig, bytes_new )

    # finally, get the loader to save our changes back to the original file
    ll.save_file( './Level000.dat' )

Open up Lemmings and change the difficulty to "Tricky". 

.. image:: doc/source/_static/leet_hacksaw.png

How about that? You master hacker you.


Okay I'm slightly intrigued, but what about image and audio data?
=================================================================

We're working on base classes and views for those. As a bonus, you don't even have to leave the Python shell to view hex or preview stuff:

.. image:: doc/source/_static/image_print.png


What if I just want to dig around without making a file format?
===============================================================

Well, you've come to the right place! Mr. Crowbar comes with plenty of general-purpose tools that can be run from the command line or through the mrcrowbar.utils module.

mrcdump (mrcrowbar.utils.hexdump)
---------------------------------

.. image:: doc/source/_static/mrcdump.png

An essential tool for any reverse engineering work, mrcdump lets you print out the contents of a file in hexadecimal bytes.

mrcdiff (mrcrowbar.utils.diff)
------------------------------

.. image:: doc/source/_static/mrcdiff.png

Got two files which are almost but not quite the same? Marvel at all the differences on a byte level with mrcdiff!

mrcfind (mrcrowbar.utils.find)
------------------------------

.. image:: doc/source/_static/mrcfind.png

The bane of translators everywhere; you need to find a piece of text in a ROM or data file, but you have no idea how it's encoded! mrcfind can search for text strings in most standard text encodings, and even brute-force an unknown text encoding based on letter patterns!

mrcgrep (mrcrowbar.utils.grep)
------------------------------

.. image:: doc/source/_static/mrcgrep.png

Have you ever used grep on a file, only to be fobbed off with the tantalising-but-useless reply of "binary file matches"? We have, and it stinks! mrcgrep won't do this to you; it supports regular expressions at the byte level, so you can satiate your need for pattern-based file searching without being constrained by the limits of plain text!

mrchist (mrcrowbar.utils.histdump)
----------------------------------

.. image:: doc/source/_static/mrchist.png

It happens; some days you get a file and need to know what it's made out of. But the file is HUGE! What could be inside? Machine code? Text? Audio? Bitmaps? DEFLATE? Encryption? Zeroes? Ones? mrchist will slice up a file and generate a histogram of the byte data, which will give you a unique fingerprint for the type of data you can expect!

mrcpix (mrcrowbar.utils.pixdump)
--------------------------------

.. image:: doc/source/_static/mrcpix.png

Does your data sort of looks like graphics? Run it through mrcpix and print out the data as a bitmap, and feast on the delicious pictures!


Contributing 
============

If you've developed models using Mr. Crowbar and want to share them with people, that's pretty great! The main source code tree is a Git repository hosted on `GitHub <https://github.com/moralrecordings/mrcrowbar>`_. Pull requests, feature requests and discussion are more than welcome. The framework is still being cooked, so not all of the interfaces are set in stone yet, but we will try to limit breaking API changes to major point releases.

Licensing
=========

Mr. Crowbar is licensed under the BSD 3-Clause license. Any code that implements or otherwise builds upon reverse engineering research produced by other individuals or groups must be attributed and cited in the header of the module.
