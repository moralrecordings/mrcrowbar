Components
==========


Blocks and Fields
-----------------

In Mr. Crowbar, the main goal is to convert raw bytes to rich data structures, and vice versa. 

We define the layout of the bytes using a class called a Block. A Block is a unit of bytes which can be broken down into a physically-grouped list of variables called Fields. (If you're familiar with C, a Block is basically the same thing as a "struct") Fields are basically rules for how to interpret the bytes in a Block; for instance, a Field of type UInt32_LE is a rule that interprets four bytes as an unsigned, little-endian 32-bit integer.

Similar to how Django does its models, the structure of a Block is defined in the class definition using Fields. Thanks to some metaclass nightmare fuel, when the Block is instantiated all of the Fields are replaced with editable properties.

Now, a tricky thing to keep in mind is that Field objects are immutable and bound to the class definition; that is, no matter how many Block objects you make, there's only ever the one copy of the Field object which gets shared amongst all of them, and so you can't store anything specific to one Block inside the Field object. 


Refs
----

Sometimes in your Blocks, you will need to cross-reference other parts of the same structure in order to read the file. For instance, you might have a file format which has a list of values preceeded by the length of the list, expecting you to parse the list then continue reading on afterwards.

Like Fields, Refs are immutable and can't hold state. Any Refs you specify in the Block class definition as e.g. arguments to Fields are created only once, and are evaluated at runtime. 


Checks
------

It would be nice to imagine that our Blocks contain only bespoke data, but that would be a lie. For instance, there's sometimes hints in the file structure so the program can ensure it is reading the right thing. This might be a "magic number" indicating the type of data, a special filler pattern for marking unused bytes, or perhaps a fancy checksum for protecting the data from those damn hacker kids you hear about on the news! 

A Check object adds a check rule to your Block with a couple of hooks; data that you import will be verified to follow the Check, and data exported will be modified to comply with the Check.


Transforms
----------

Unfortunately, not every binary file format is basic enough to be directly mapped to a big collection of numbers and strings. Hand-rolled compression formats and silly obfuscation schemes are popular, especially for files which (at the time) needed to fit onto a floppy disk. As you can guess, trying to define these wacky algorithms using a reversible schema like Blocks and Fields would be painful and take forever, so this is where we take advantage of executable Python code. At the end of the day, the meat inside these weirdo files has to be properly structured in memory for a program to make use of them, so the 90% use case is converting what we'll call "insane binary" into "readable binary".

The Transform class is a unit operation which (as you might guess) **transforms** a set of bytes, from a complicated format into a simple format that can e.g. be modelled as a Mr. Crowbar Block. To use it you must implement two methods, import_data() and export_data(), which perform the forward and reverse variants (respectively) of the transform. Unlike Blocks, you don't get anything for free; you can choose to write only the import_data() method for instance, but that will prevent you from saving the resulting files!

(After all, most sane people hate writing compressors. My advice? If you need to get something off the ground and your insane binary format has a "copy these next n bytes verbatim" command, use that. Disk space is cheap.)

But how does this get added into the model? See, a handful of Field types (Bytes, BlockField, BlockStream) support passing a Transform object in as an argument, meaning at load time the data will first be passed through the forward transform, and at save time back through the reverse transform. It's bulletproof!


Views
-----

Views can be considered as a sort of reusable window, letting you peer into and modify the contents of a Block in a context-sensitive way. Think of Views as a modular way to extend the features of a Block class that's less crap than mixins.

For example, suppose you have a Block which represents an indexed image (i.e. a picture with a limited colour palette). The Block may contain a UInt16 for the width, a UInt16 for the height, a lump of bytes representing the palette (which we expose as a BlockList full of Colours), and a much bigger chunk of bytes containing the image data (each byte being a pixel in the image). 

Now, we *could* expose the image bytes as another list full of UInt8s, but that wouldn't be very fun; we would waste a bunch of time on glue code outside of Mr. Crowbar to get to where we actually want to be (i.e. viewing and editing stuff as a Python image type). Instead, we can wire all these fields up to an IndexedImage View, which acts as an automatic bridge between Mr. Crowbar and Python's Pillow imaging library. IndexedImage will provide the image you've specified in Pillow's native Image type, and as a bonus you can even print it to a terminal with state-of-the-art ANSI escape sequence technology. The best part? Changes to the image pushed through the view will automatically flow back to their respective Fields. 

I know you've been crying out for something that will let you hold state, and you'll be pleased to hear that Views can do just that. As a side effect you will need to define Views in your Block's __init__ method; the first argument to a View's constructor is the parent Block object, so having them in the Class definition along with the Fields won't cut it. 
