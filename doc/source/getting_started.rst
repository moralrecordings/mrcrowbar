
Getting Started
===============

Requirements
------------

Mr. Crowbar requires Python 3. This was a design decision; Python 2 pretty much considers strings and byte streams to be the same thing (plus a seperate Unicode string type few people bother with), which historically has lead to a lot of dodgy handling to make the two ideas interoperate. Python 3 has fixed this: the string type is now always byte-independent Unicode, and we have proper bytes and bytearray types! Python 2.7 did try to shim the gap by adding aliases for both of these, but they are not exactly the same and complex operations will flake out. So because I have limited time and don't really want the codebase to devolve into Six spaghetti, we're sticking to just Python 3 for now.


