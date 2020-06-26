Wait, what?!
============

Mr. Crowbar is a Django-esque model framework that makes it super easy to work with proprietary binary formats while reverse engineering. 

File formats are described with Python classes that allow ORM-like free modification of structures and properties, which in turn can be validated and converted back to the binary equivalent at any time.

The eventual goal is to provide a library for storing file format information that retains the readability of a text file, while providing instant read/write support for almost no cost.

Give us an example
==================

The `README <https://moral.net.au/mrcrowbar>`_ has a pretty good example, omitted here for brevity.

Contributing 
============

If you've developed models using Mr. Crowbar and want to share them with people, that's pretty great! The main source code tree is a Git repository hosted on `GitHub <https://github.com/moralrecordings/mrcrowbar>`_. Pull requests, feature requests and discussion are more than welcome. The framework is still being cooked, so not all of the interfaces are set in stone yet, but we will try to limit breaking API changes to major point releases.

Licensing
=========

Mr. Crowbar is licensed under the BSD 3-Clause license. Any code that implements or otherwise builds upon reverse engineering research produced by other individuals or groups must be attributed and cited in the header of the module.
