import unittest

import enum

from mrcrowbar import models as mrc

class TestBlock( unittest.TestCase ):
    def test_chain( self ):
        class TestEnum( enum.IntEnum ):
            SUCCESS = 1
            FAILURE = -1

        class Test( mrc.Block ):
            field1 = mrc.UInt16_BE( 0x00 )
            field2 = mrc.Int32_LE()
            field3 = mrc.Bits8( 0x08, bits=0b00111100 )
            field4 = mrc.Bits8( 0x08, bits=0b11000011 )
            field5 = mrc.Int8( enum=TestEnum )

        payload = b'\x12\x34\x78\x56\x34\x12\x00\x00\x96\xff'
        test = Test( payload )
        self.assertEqual( test.field1, 0x1234 )
        self.assertEqual( test.field2, 0x12345678 )
        self.assertEqual( test.field3, 0x05 )
        self.assertEqual( test.field4, 0x0a )
        self.assertEqual( test.field5, -1 )
        self.assertEqual( test.export_data(), payload )

        test.field5 = 0
        with self.assertRaises( mrc.FieldValidationError ):
            test.export_data()

    def test_sizing( self ):
        class Test( mrc.Block ):
            field1 = mrc.UInt8( 0x00 )
            field2 = mrc.UInt8( 0x09 )

        test = Test()
        self.assertEqual( test.get_size(), 0x0a )


class TestBlockField( unittest.TestCase ):
    def test_block_count( self ):
        class Element( mrc.Block ):
            field1 = mrc.UInt8()
            field2 = mrc.UInt8()
        
        class Test( mrc.Block ):
            field = mrc.BlockField( Element, count=3 )

        payload = b'\x12\x34\x56\x78\x9a\xbc\xde\xf0'

        test = Test( payload )
        self.assertEqual( test.field[0].field1, 0x12 )
        self.assertEqual( test.field[0].field2, 0x34 )
        self.assertEqual( test.field[1].field1, 0x56 )
        self.assertEqual( test.field[1].field2, 0x78 )
        self.assertEqual( test.field[2].field1, 0x9a )
        self.assertEqual( test.field[2].field2, 0xbc )
        self.assertEqual( test.export_data(), payload[:6] )

    def test_block_stream( self ):
        class Element( mrc.Block ):
            field1 = mrc.UInt8()
            field2 = mrc.UInt8()
        
        class Test( mrc.Block ):
            field = mrc.BlockField( Element, stream=True )

        payload = b'\x12\x34\x56\x78\x9a\xbc\xde\xf0'

        test = Test( payload )
        self.assertEqual( test.field[0].field1, 0x12 )
        self.assertEqual( test.field[0].field2, 0x34 )
        self.assertEqual( test.field[1].field1, 0x56 )
        self.assertEqual( test.field[1].field2, 0x78 )
        self.assertEqual( test.field[2].field1, 0x9a )
        self.assertEqual( test.field[2].field2, 0xbc )
        self.assertEqual( test.field[3].field1, 0xde )
        self.assertEqual( test.field[3].field2, 0xf0 )
        self.assertEqual( test.export_data(), payload )

    def test_block_stream_end( self ):
        class Element( mrc.Block ):
            field1 = mrc.UInt8()
            field2 = mrc.UInt8()

        class Test( mrc.Block ):
            field = mrc.BlockField( Element, stream=True, stream_end=b'\x9a\xbc' )
            padding = mrc.Bytes()

        payload = b'\x12\x34\x56\x78\x9a\xbc\xde\xf0'

        test = Test( payload )
        self.assertEqual( test.field[0].field1, 0x12 )
        self.assertEqual( test.field[0].field2, 0x34 )
        self.assertEqual( test.field[1].field1, 0x56 )
        self.assertEqual( test.field[1].field2, 0x78 )
        self.assertEqual( test.padding, b'\xde\xf0' )
        self.assertEqual( test.export_data(), payload )

    def test_block_stop_check( self ):
        class Element( mrc.Block ):
            field1 = mrc.UInt8()
            field2 = mrc.UInt8()

        STOP = b'\x9a\xbc'

        def stop_check( buffer, offset ):
            return buffer[offset:offset+2] == STOP

        class Test( mrc.Block ):
            field = mrc.BlockField( Element, stream=True, stop_check=stop_check )
            backstop = mrc.Const( mrc.Bytes( mrc.EndOffset( 'field' ), length=2 ), STOP )
            padding = mrc.Bytes( mrc.EndOffset( 'backstop' ) )

        payload = b'\x12\x34\x56\x78\x9a\xbc\xde\xf0'

        test = Test( payload )
        self.assertEqual( test.field[0].field1, 0x12 )
        self.assertEqual( test.field[0].field2, 0x34 )
        self.assertEqual( test.field[1].field1, 0x56 )
        self.assertEqual( test.field[1].field2, 0x78 )
        self.assertEqual( test.padding, b'\xde\xf0' )
        self.assertEqual( test.export_data(), payload )


class TestStringField( unittest.TestCase ):
    def test_fixed_pad( self ):
        payload = b'abcd\x00\x00\x00\x00efghijklmn\x00\x00\x00\x00\x00\x00'

        class Test( mrc.Block ):
            field = mrc.StringField( count=3, element_length=8, zero_pad=True )

        test = Test( payload )
        self.assertEqual( test.field[0], b'abcd' )
        self.assertEqual( test.field[1], b'efghijkl' )
        self.assertEqual( test.field[2], b'mn' )
        self.assertEqual( test.export_data(), payload )


class TestNumberFields( unittest.TestCase ):

    def test_endian( self ):
        class TestL( mrc.Block ):
            i16 = mrc.Int16_LE()
            i24 = mrc.Int24_LE()
            i32 = mrc.Int32_LE()
            i64 = mrc.Int64_LE()
            ui16 = mrc.UInt16_LE()
            ui24 = mrc.UInt24_LE()
            ui32 = mrc.UInt32_LE()
            ui64 = mrc.UInt64_LE()
            f32 = mrc.Float32_LE()
            f64 = mrc.Float64_LE()

        class TestB( mrc.Block ):
            i16 = mrc.Int16_BE()
            i24 = mrc.Int24_BE()
            i32 = mrc.Int32_BE()
            i64 = mrc.Int64_BE()
            ui16 = mrc.UInt16_BE()
            ui24 = mrc.UInt24_BE()
            ui32 = mrc.UInt32_BE()
            ui64 = mrc.UInt64_BE()
            f32 = mrc.Float32_BE()
            f64 = mrc.Float64_BE()

        class TestLP( mrc.Block ):
            _endian = 'little'

            i16 = mrc.Int16_P()
            i24 = mrc.Int24_P()
            i32 = mrc.Int32_P()
            i64 = mrc.Int64_P()
            ui16 = mrc.UInt16_P()
            ui24 = mrc.UInt24_P()
            ui32 = mrc.UInt32_P()
            ui64 = mrc.UInt64_P()
            f32 = mrc.Float32_P()
            f64 = mrc.Float64_P()

        class TestBP( TestLP ):
            _endian = 'big'

        payload_big = b'\x12\x34\x12\x34\x56\x12\x34\x56\x78\x12\x34\x56\x78\x9a\xbc\xde\xf0\x12\x34\x12\x34\x56\x12\x34\x56\x78\x12\x34\x56\x78\x9a\xbc\xde\xf0\x47\x00\x00\x00\x40\xe0\x00\x00\x00\x00\x00\x00'

        payload_little = b'\x34\x12\x56\x34\x12\x78\x56\x34\x12\xf0\xde\xbc\x9a\x78\x56\x34\x12\x34\x12\x56\x34\x12\x78\x56\x34\x12\xf0\xde\xbc\x9a\x78\x56\x34\x12\x00\x00\x00\x47\x00\x00\x00\x00\x00\x00\xe0\x40'

        CASES = (
            (TestL, payload_little),
            (TestB, payload_big),
            (TestLP, payload_little),
            (TestBP, payload_big),
        )


        for klass, payload in CASES:
            test = klass( payload )
            self.assertEqual( test.i16, 0x1234 )
            self.assertEqual( test.i24, 0x123456 )
            self.assertEqual( test.i32, 0x12345678 )
            self.assertEqual( test.i64, 0x123456789abcdef0 )
            self.assertEqual( test.ui16, 0x1234 )
            self.assertEqual( test.ui24, 0x123456 )
            self.assertEqual( test.ui32, 0x12345678 )
            self.assertEqual( test.ui64, 0x123456789abcdef0 )
            self.assertEqual( test.f32, 32768.0 )
            self.assertEqual( test.f64, 32768.0 )
            self.assertEqual( test.export_data(), payload )


if __name__ == '__main__':
    unittest.main()
