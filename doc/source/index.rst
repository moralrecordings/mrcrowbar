
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

I was kind of taken aback at how non-standardised this field of reverse engineering was. Everyone seems to have a story of writing their own tools and solving identical problems over and over again for each target.

Take game mods and ROM hacks. The golden age of game modding firmly predates the recent mainstreaming of publishing as open source. Visit gbatemp.net or romhacking.net and you'll find hundreds of game specific hand-rolled tools from years past; none of them actively maintained, nearly all of them without source code. For other areas it's just text; thousands of text files explaining what a proprietary format does. These documents are mostly static, and could disappear from the internet at any second.

Deep down, I hope that putting together something like this makes activities like game modding more accessible to a wider group of people. A lot of talented developers got their start by reverse engineering; in the case of game mods building upon a solid foundation of assets and code along with a strong network of fans. Reverse engineering gives you knowledge of how systems work in the real world and why; an education you can't get from following examples or reading StackOverflow.


What's with the name?
---------------------

No reason for the name, other than "crowbar" was taken. Despite the honorific the prybar with the googly eyes is, like countless corporate mascots before it, a magical pan-sexual non-threatening spokesthing. Also there's an unfortunate Redmond connotation to any software that begins with the letters "ms".


.. toctree::
   :hidden:

   getting_started
   components
   modules

