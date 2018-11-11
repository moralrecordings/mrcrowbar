Components
==========

Blocks and Fields
-----------------

In Mr. Crowbar, the goal is to convert raw bytes to editable data structures, and vice versa. 

For a byte format, the layout is defined with a ``Block``. A ``Block`` is used to model any slab of bytes which can be broken down into a physically-grouped collection of values, such as numbers, strings or other ``Block`` classes. (If you're familiar with C, a ``Block`` is basically the same thing as a ``struct``) 

Similar to Django models, the structure of a ``Block`` is laid out in the class using ``Field`` definitions. ``Field`` definitions are basically rules for how to interpret the bytes in a ``Block``; for instance, a ``Field`` of type ``UInt32_LE`` is a rule that interprets four bytes as an unsigned, little-endian 32-bit integer. Ideally there should be a ``Field`` definition for every section of data in a ``Block``, even if it's just a placeholder to copy the raw bytes, otherwise it will be left out of the conversion process.

Thanks to some metaclass nightmare fuel, when a ``Block`` is instantiated, all of the ``Field`` definitions turn into editable properties. Now, a tricky thing to keep in mind is that ``Field`` definitions are immutable; that is, there's only ever the one copy of the ``Field`` object which gets shared amongst all of the ``Block`` objects of the same type. So you can't store anything specific to one ``Block`` inside the ``Field`` object!

Field classes
-------------

Mr. Crowbar provides a selection of built-in ``Field`` classes for your writing enjoyment.

Bytes
*****

``Bytes`` is probably the simplest ``Field`` class there is; it will return raw data from the file as a Python byte string. By default ``Bytes`` will keep reading until it reaches the end of the imported data, but usually there's a size you'd want to pass to the ``length`` parameter. Also, ``Bytes`` can be a useful stopgap to copy unknown chunks without any change. 

NumberField
***********






Refs
----

Sometimes when reading a Block, you will need to cross-reference other parts of the same structure. For instance, you might have a file format which has a list of items preceded by the length of the list. In this case you would want the parser to read the length first, then read in the correct number of list items. 

As an addendum, the file format might expect you to parse the list then continue reading on afterwards. This is possible using EndOffset, a special Ref which returns the end offset of a particular field.

Like Fields, Refs are immutable and can't hold state. Any Refs you specify in the Block class definition as e.g. arguments to Fields are created only once, and are evaluated at runtime. 


Checks
------

It would be nice to imagine that our Blocks contain only useful data that's repeated once, but that would be a lie. For instance, there's sometimes data in the file structure that are hints for the parser; such as a "magic number" indicating the type of data, a special filler pattern for marking unused bytes, or perhaps a fancy checksum for protecting the data from those damn hacker kids you hear about on the news! 

A Check object adds a check rule to your Block with a couple of hooks; data that you import will be verified to follow the Check, and data exported will be modified to comply with the Check.


Transforms
----------

Unfortunately, not every binary file format is basic enough to be directly mapped to a big collection of numbers and strings. Hand-rolled compression formats and silly obfuscation schemes are popular, especially for files which (at the time) needed to fit onto a floppy disk. As you can guess, trying to define these wacky algorithms using a reversible schema like Blocks and Fields would be painful and take forever, so this is where we take advantage of executable Python code. At the end of the day, the meat inside these weirdo files has to be properly structured in memory for a program to make use of them, so the 90% use case is converting what we'll call "insane binary" into "readable binary".

The Transform class is a unit operation which (as you might guess) **transforms** a set of bytes, from a complicated format into a simple format that can e.g. be modelled as a Mr. Crowbar Block. To use it you must implement two methods, import_data() and export_data(), which perform the forward and reverse variants (respectively) of the transform. Unlike Blocks, you don't get anything for free; you can choose to write only the import_data() method for instance, but that will prevent you from saving the resulting files!

(After all, most sane people hate writing compressors. My advice? Disk space is cheap; find the equivalent of a "copy these next n bytes exactly" command and use that.)

But how does this get added into the model? See, a handful of Field types (Bytes, BlockField) support passing a Transform object in as an argument, meaning at load time the data will first be passed through the forward transform, and at save time back through the reverse transform. It's bulletproof!


Views
-----

Views can be considered as a sort of reusable window, letting you peer into and modify the contents of a Block in a context-sensitive way. Think of Views as a modular way to extend the features of a Block class that's less crap than mixins.

For example, suppose you have a Block which represents an indexed image (i.e. a picture with a limited colour palette). The Block may contain a UInt16 for the width, a UInt16 for the height, a lump of bytes representing the palette (which we expose as a BlockList full of Colours), and a much bigger chunk of bytes containing the image data (each byte being a pixel in the image). 

Now, we *could* expose the image bytes as another list full of UInt8s, but that wouldn't be very fun; we would waste a bunch of time on glue code outside of Mr. Crowbar to get to where we actually want to be (i.e. viewing and editing stuff as a Python image type). Instead, we can wire all these fields up to an IndexedImage View, which acts as an automatic bridge between Mr. Crowbar and Python's Pillow imaging library. IndexedImage will provide the image you've specified in Pillow's native Image type, and as a bonus you can even print it to a terminal with state-of-the-art ANSI escape sequence technology. The best part? Changes to the image pushed through the view will automatically flow back to their respective Fields. 

I know you've been crying out for something that will let you hold state, and you'll be pleased to hear that Views can do just that. As a side effect you will need to define Views in your Block's __init__ method; the first argument to a View's constructor is the parent Block object, so having them in the class definition along with the Fields won't cut it. 
