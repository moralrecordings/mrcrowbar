
Mr. Crowbar
===========

Ever encountered some crusty binary data format, and the only tool to unpack it stopped running in the late 80s? Do you experience frustration that, despite advances in reverse engineering technology, there's no easier way of documenting file formats than dumb text files or C code? Would you like to mod old games without the agonizing experience of rolling your own tools?

.. image:: _static/mrcrowbar.svg

If you answered yes... I hate to say it but you're pretty weird, and you're *also* the perfect candidate for **Mr. Crowbar!** Mr. Crowbar is a model framework (similar to Django) for binary data. It is also a (nascent) encyclopedia of unloved file formats, such as the hand-crafted monstrosities beloved by early game designers.

The goal of Mr. Crowbar is to offer transparent, constraint-based reading and editing of files. You should be able to write a model describing your target files and load them all in as structured Python objects. Assuming you provide enough detail, you should also be able to write all your changes back in the original format.


.. toctree::
   :maxdepth: 2

