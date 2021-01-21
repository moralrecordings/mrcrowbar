Changelog
#########

Unreleased
==========
- lib.hardware.tispeech: Init
- lib.hardware.tispeech: Add TMS0280 constants
- lib.hardware.tispeech: Add SpeakAndSpellROM
- sound: Replace pyaudio with miniaudio

0.9.0 - 2021-01-14
==================
- common.bounds: Allow negative indexing for hexdumps etc.
- blocks.Block: Fall back to Unknown for child Blocks that fail to parse
- utils: Add find, find_encoded and find_unknown functions
- ansi.HexdumpHighlightBuffer: Split out logic for rendering highlighted hexdumps
- encoding.regex_pattern_to_bytes: Fix matching for UTF16 and UTF32
- utils: Merge hexdump_grep and listdump_grep into grepdump
- utils: Merge find_encoded and find_unknown into find
- cli: Add mrcfind tool
- utils.find_iter: Add support for multiple search terms
- cli: Rework arguments, remove stats from hexdump
- cli: mrcdiff now can be run on two directories
- checks: Add Pointer class for tracking in-file offsets

0.8.0 - 2020-07-03
==================
- cli.mrcdump: Add support for hiding offsets and glyphs.
- blocks.Block: Use better wording in debug mode.
- lib.platforms.director: Start tracking how V4 files are interpreted in DirectorV4Parser.
- lib.platforms.director.DirectorV4Parser: Add code dumper
- fields.Bits: Fix 32 and 64 bit support
- lib.games.sam: Fix typo
- lib.platforms.director: Fix implementation of ScriptFloat
- blocks.Block: More debug logs
- blocks.Block: Fix missing line in get_field_obj
- lib.platforms.director: Improve SoundV4, add bitmap support to parser
- encoding.regex_pattern_to_bytes: Fix fixed_string processing of backslash
- bits.BitWriter: Add input_reverse option
- bits.BitStream: Add new, overhauled bit manipulation engine
- lib.platforms.director.ConfigV4: Add struct, checksum generator
- lib.images.base: Fix keyword usage, naming collision
- lib.platforms.director.unlock_dir_file: Add helper for unlocking Director files
- lib.games.lemmings: Replace BitReader with BitStream
- fields: Annotate errors with position in the block tree
- blocks: Improve docstrings
- bits.BitStream: Implement seek(), remove old BitReader/BitWriter classes

0.7.3 - 2019-12-07
==================

- utils.grep: Fix wrong number of arguments.
- utils.diff: Fix comparison between different bytes types.
- lib.platforms.director: Add IMapV4, fix ScriptCastV4.

0.7.2 - 2019-11-24
==================

- lib.platforms.director: More improvements.
- lib.platforms.director: Add ScriptGlobal model, fix ScriptV4/ScriptFunction specification.
- cli.mrcgrep: Add ability to ignore case.
- encoding.regex_pattern_to_bytes: Fix parsing of repetition blocks.
- views.StoreRef: Make size argument optional by default.
- lib.platforms.director: Add ScriptArguments and ScriptVariables.
- bits: Init, move specialist methods out of utils.
- fields.StreamField: Fix get_size().
- utils: Add search() method for searching within Blocks for Fields that match byte strings.
- fields.StreamField: Prevent massive recursive slowdown in get_size().
- sound.play_pcm: Fix playback for case with no interpolation.


0.7.1 - 2019-10-25
==================

- encoding: Add regex_pattern_to_bytes() for converting UTF8 format string into a byte regular expression.
- utils.grep_iter: Create a base method for regular expression based searching.
- common: Add file_path_recurse() to recursively find file paths.
- cli: Update command line tools to support recursive directory traversal.
- Add changelog.
- cli.mrcgrep: Add command line binary grep tool.
- utils.diff: Rename to utils.diffdump.
- utils.diff_iter: Decouple diff results from print output.
- lib.os.win16.RelocationOSFixup: Add enum for fixup types.
- utils.diffdump: Return True if the two sources match.

0.7.0 - 2019-09-26
==================

- fields: Update the string Field classes (e.g. Bytes, CString) to be based on StringField. This allows multiple elements.
- fields.ChunkField: Allow using an enum class for chunk IDs.
- lib.containers.vgm: Add preliminary support for VGM files.
- tests: Improve test coverage.
- fields.StreamField: get_from_buffer() changed to fail if there's no data left.
- lib.platforms.director: More improvements to Macromedia Director support.
- fields: Change Field classes to disallow unnamed arguments except klass and offset. This improves readability and makes argument ordering less brittle.
- lib.images.base: Fix IndexedImage to not crash out of bounds and fall back to TEST_PALETTE by default.
- ansi: Add escape sequences for clearing the screen and moving the cursor.
- lib.games.lomax: Add preliminary support for Adventures of Lomax graphics data.

0.6.1 - 2019-07-06
==================

- lib.games.jill: Add audio support, fix load ordering and class invocations.
- lib.audio.voc: Add preliminary support for Creative VOC files.
- encoding: Add support for 24-bit integers.
- fields: Add Fields for decoding variants of Int24.
- views.Store: Add support for inline Transforms.
- lib.os.dos.B800Char: Add ANSI support for blinking text.
- lib.platforms.director: More improvements to Macromedia Director support, add a Lingo disassembler.
- lib.games.boppin: Add inline decompression to loader.
- fields.Bytes: Add support for alignment.
- utils.pixdump: Add a shortcut for displaying data as a 256 colour image.
- fields.BlockField: Fix updating the dependencies on child objects on save.
- utils: Split out the console-output parts into the new ansi module.
- utils: Split out the colour-handling parts into the new colour module.
- lib.audio.base: Split out the PCM playback code into the new sound module.
- utils: Move some low-level methods into the new common module, to avoid importing utils everywhere.
- fields.ChunkField: Allow None as a chunk payload.
- refs.Ref: Start enforcing immutability.
- common: Add a serialise() method for Fields.
- utils: Add a diff() tool for comparing Blocks.
- sound: Fix multichannel support and resampling.
- .travis.yml: Add CI for running tests.

0.6.0 - 2019-01-13
==================

0.5.1 - 2018-07-20
==================

0.5.0 - 2018-06-22
==================

0.4.2 - 2018-02-05
==================

0.4.1 - 2017-11-26
==================

0.4.0 - 2017-10-12
==================


