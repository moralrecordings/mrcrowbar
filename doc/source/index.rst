
Mr. Crowbar
===========

.. image:: _static/mrcrowbar.png

Wait, what?!
------------

Mr. Crowbar is a Django-esque model framework that makes it super easy to work with proprietary binary formats while reverse engineering. 

File formats are described with Python classes that allow ORM-like free modification of structures and properties, which in turn can be validated and converted back to the binary equivalent at any time.

The eventual goal is to provide a library for storing file format information that retains the readability of a text file, while providing instant read/write support for almost no cost.


But why?!?
----------

I was kind of taken aback at how non-standardised this area of reverse engineering was. There are countless stories of people writing their own tools and solving identical problems over and over again for each target.

Take game modifications and ROM hacks. Visit gbatemp.net or romhacking.net and you'll find thousands of different game-specific tools; many retreading the same ground (e.g. graphics editors), none of them actively maintained, nearly all of them without source code. It's good that these tools exist; they let people make reasonably complex mods without low-level experience. But all the knowledge the author has collected about the formats and mechanics of the game is locked up in the tool! For 

The closest thing to a standard is the written word; there are thousands of text files and websites that explain how an individual proprietary format works. While valuable from an educational standpoint, there's still a reasonably high barrier to entry; even a skilled developer would balk at writing a whole bunch of boilerplate just to edit a file!

Deep down, I hope that a framework like this will make reversing activities more accessible to a wider group of people. A lot of talented developers and designers get their start by reverse engineering, as it delivers a hands-on understanding of how real world systems are designed, better than any tutorial or textbook. Right now it seems like there's a handful of gatekeepers trying to keep this area for themselves, and to hell with that.


What's with the name?
---------------------

No reason for the name, other than "crowbar" was taken in PyPi. Despite the honorific the prybar with the googly eyes is, like countless corporate mascots before it, a magical pan-sexual non-threatening spokesthing. Also there's an unfortunate Redmond connotation to any software that begins with the letters "ms".


.. toctree::
   :hidden:

   getting_started
   components
   utilities
   modules

