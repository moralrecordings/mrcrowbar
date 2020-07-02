import unittest

import enum

from mrcrowbar import bits
from mrcrowbar import models as mrc
from mrcrowbar import sound

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


class TestChunk( unittest.TestCase ):
    def test_chunk( self ):
        class Data1( mrc.Block ):
            length = mrc.UInt8( 0x00 )
            payload = mrc.Bytes( 0x01, length=mrc.Ref( 'length' ) )

        class Data2( mrc.Block ):
            payload = mrc.UInt32_LE( 0x00 )

        CHUNK_MAP = {
            b'\x01': Data1,
            b'\x02': Data2
        }

        class Test( mrc.Block ):
            data = mrc.ChunkField( CHUNK_MAP, 0x00, stream_end=b'\x00', id_size=1 )
            bonus = mrc.Bytes( mrc.EndOffset( 'data' ) )

        payload = b'\x01\x06abcdef\x02\x78\x56\x34\x12\x01\x02gh\x00end'

        test = Test( payload )
        self.assertEqual( len( test.data ), 3 )
        self.assertIsInstance( test.data[0], mrc.Chunk )
        self.assertIsInstance( test.data[1], mrc.Chunk )
        self.assertIsInstance( test.data[2], mrc.Chunk )
        self.assertEqual( test.data[0].id, b'\x01' )
        self.assertEqual( test.data[1].id, b'\x02' )
        self.assertEqual( test.data[2].id, b'\x01' )
        self.assertIsInstance( test.data[0].obj, Data1 )
        self.assertIsInstance( test.data[1].obj, Data2 )
        self.assertIsInstance( test.data[2].obj, Data1 )
        self.assertEqual( test.data[0].obj.payload, b'abcdef' )
        self.assertEqual( test.data[1].obj.payload, 0x12345678 )
        self.assertEqual( test.data[2].obj.payload, b'gh' )
        self.assertEqual( test.bonus, b'end' )
        self.assertEqual( test.export_data(), payload )

    def test_chunk_varlength( self ):
        class Data1( mrc.Block ):
            payload = mrc.Bytes( 0x00 )

        class Data2( mrc.Block ):
            payload = mrc.Bytes( 0x00 )

        CHUNK_MAP = {
            0x12: Data1,
            0x34: Data2,
        }

        class Test( mrc.Block ):
            data = mrc.ChunkField( CHUNK_MAP, 0x00, stream_end=b'\xff', id_field=mrc.UInt8, length_field=mrc.UInt8, fill=b'\x00' )
            bonus = mrc.Bytes( mrc.EndOffset( 'data' ) )

        payload = b'\x12\x04abcd\x34\x06efghij\x12\x01\x00\x12\x01\x00\x12\x02kl\xffend'

        test = Test( payload )
        self.assertEqual( len( test.data ), 5 )
        self.assertIsInstance( test.data[0], mrc.Chunk )
        self.assertIsInstance( test.data[1], mrc.Chunk )
        self.assertIsInstance( test.data[2], mrc.Chunk )
        self.assertIsInstance( test.data[3], mrc.Chunk )
        self.assertIsInstance( test.data[4], mrc.Chunk )
        self.assertEqual( test.data[0].id, 0x12 )
        self.assertEqual( test.data[1].id, 0x34 )
        self.assertEqual( test.data[2].id, 0x12 )
        self.assertEqual( test.data[3].id, 0x12 )
        self.assertEqual( test.data[4].id, 0x12 )
        self.assertIsInstance( test.data[0].obj, Data1 )
        self.assertIsInstance( test.data[1].obj, Data2 )
        self.assertIsNone( test.data[2].obj )
        self.assertIsNone( test.data[3].obj )
        self.assertIsInstance( test.data[4].obj, Data1 )
        self.assertEqual( test.data[0].obj.payload, b'abcd' )
        self.assertEqual( test.data[1].obj.payload, b'efghij' )
        self.assertEqual( test.data[4].obj.payload, b'kl' )
        self.assertEqual( test.bonus, b'end' )
        self.assertEqual( test.export_data(), payload )


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

    def test_stream( self ):
        payload = b'abcd\x00ef\x00gh\x00'

        class Test( mrc.Block ):
            field = mrc.StringField( stream=True, element_end=b'\x00' )
        test = Test( payload )
        self.assertEqual( len( test.field ), 3 )
        self.assertEqual( test.field[0], b'abcd' )
        self.assertEqual( test.field[1], b'ef' )
        self.assertEqual( test.field[2], b'gh' )
        self.assertEqual( test.export_data(), payload )

    def test_length_field( self ):
        payload = b'\x04\x02ab\x03cde\x04fghi\x01j'

        class Test( mrc.Block ):
            count = mrc.UInt8( 0x00 )
            field = mrc.StringField( 0x01, count=mrc.Ref( 'count' ), length_field=mrc.UInt8 )

        test = Test( payload )
        self.assertEqual( len( test.field ), test.count )
        self.assertEqual( test.field[0], b'ab' )
        self.assertEqual( test.field[1], b'cde' )
        self.assertEqual( test.field[2], b'fghi' )
        self.assertEqual( test.field[3], b'j' )
        self.assertEqual( test.export_data(), payload )

        payload_mod = b'\x03\x02ab\x03cde\x01j'
        del test.field[2]
        self.assertEqual( test.export_data(), payload_mod )

    def test_transform( self ):
        payload = b'\x01\x23\x45\x67'

        class TestTransform( mrc.Transform ):
            def import_data( self, buffer, parent=None ):
                output = bytearray( len( buffer )*2 )
                for i in range( len( buffer ) ):
                    output[2*i] = buffer[i] >> 4
                    output[2*i+1] = buffer[i] & 0x0f
                return mrc.TransformResult( payload=bytes( output ), end_offset=len( buffer ) )

            def export_data( self, buffer, parent=None ):
                output = bytearray( len( buffer )//2 )
                for i in range( len( output ) ):
                    output[i] |= buffer[2*i] << 4
                    output[i] |= buffer[2*i+1]
                return mrc.TransformResult( payload=bytes( output ), end_offset=len( buffer ) )

        class Test( mrc.Block ):
            field = mrc.StringField( 0x00, transform=TestTransform() )

        test = Test( payload )
        self.assertEqual( test.field, b'\x00\x01\x02\x03\x04\x05\x06\x07' ) 
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


class TestStore( unittest.TestCase ):

    def test_store( self ):
        class Element( mrc.Block ):
            data = mrc.Bytes( 0x00 )

        class ElementRef( mrc.Block ):
            offset = mrc.UInt8( 0x00 )
            size = mrc.UInt8( 0x01 )

            ref = mrc.StoreRef( Element, mrc.Ref( '_parent.store' ), mrc.Ref( 'offset' ), mrc.Ref( 'size' ) )

        class Test( mrc.Block ):
            count = mrc.UInt8( 0x00 )
            elements = mrc.BlockField( ElementRef, count=mrc.Ref( 'count' ) )
            raw_data = mrc.Bytes( mrc.EndOffset( 'elements' ) )

            def __init__( self, *args, **kwargs ):
                self.store = mrc.Store( 
                    self, mrc.Ref( 'raw_data' )
                )
                super().__init__( *args, **kwargs )

        payload = b'\x04\x00\x02\x02\x03\x05\x01\x06\x02abcdefgh'
        test = Test( payload )
        self.assertEqual( test.elements[0].ref.data, b'ab' )
        self.assertEqual( test.elements[1].ref.data, b'cde' )
        self.assertEqual( test.elements[2].ref.data, b'f' )
        self.assertEqual( test.elements[3].ref.data, b'gh' )
        self.assertEqual( test.export_data(), payload )

        test.elements[2].ref.data = b'xxx'
        test.store.save()
        new_payload = b'\x04\x00\x02\x02\x03\x05\x03\x08\x02abcdexxxgh'
        self.assertEqual( test.elements[0].ref.data, b'ab' )
        self.assertEqual( test.elements[1].ref.data, b'cde' )
        self.assertEqual( test.elements[2].ref.data, b'xxx' )
        self.assertEqual( test.elements[3].ref.data, b'gh' )
        self.assertEqual( test.export_data(), new_payload )



    def test_linear_offsets( self ):
        class Element( mrc.Block ):
            data = mrc.Bytes( 0x00 )

        class Test( mrc.Block ):
            count = mrc.UInt8( 0x00 )
            offsets = mrc.UInt16_LE( 0x01, count=mrc.Ref( 'count' ) )
            raw_data = mrc.Bytes( mrc.EndOffset( 'offsets' ) )

            def __init__( self, *args, **kwargs ):
                self.elements = mrc.LinearStore(
                    self, mrc.Ref( 'raw_data' ), Element,
                    offsets=mrc.Ref( 'offsets' )
                )
                super().__init__( *args, **kwargs )
            
        payload = b'\x04\x00\x00\x02\x00\x06\x00\x09\x00abcdefghij'

        test = Test( payload )
        self.assertEqual( len( test.elements.items ), 4 )
        self.assertEqual( test.elements.items[0].data, b'ab' )
        self.assertEqual( test.elements.items[1].data, b'cdef' )
        self.assertEqual( test.elements.items[2].data, b'ghi' )
        self.assertEqual( test.elements.items[3].data, b'j' )
        self.assertEqual( test.export_data(), payload )

        del test.elements.items[1]
        test.elements.save()
        new_payload = b'\x03\x00\x00\x02\x00\x05\x00abghij'
        self.assertEqual( test.export_data(), new_payload )


class TestBits( unittest.TestCase ):
    def test_bits_read( self ):
        data = bytes([0b10010010, 0b01001010, 0b10101010, 0b10111111])

        bs = bits.BitStream( data )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 14 ), 0b10101010101010 )

        bs = bits.BitStream( data, io_endian='little' )
        self.assertEqual( bs.read( 3 ), 0b001 )
        self.assertEqual( bs.read( 3 ), 0b001 )
        self.assertEqual( bs.read( 3 ), 0b001 )
        self.assertEqual( bs.read( 3 ), 0b001 )
        self.assertEqual( bs.read( 14 ), 0b01010101010101 )

        bs = bits.BitStream( data, bytes_reverse=True )
        self.assertEqual( bs.read( 17 ), 0b10111111101010100 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 4 ), 0b1010 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )

        bs = bits.BitStream( data, bytes_reverse=True, io_endian='little', bit_endian='little' )
        self.assertEqual( bs.read( 6 ), 0b111111 )
        self.assertEqual( bs.read( 14 ), 0b10101010101010 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )
        self.assertEqual( bs.read( 3 ), 0b100 )

    def test_bits_write( self ):
        target = bytes([0b10010010, 0b01001010, 0b10101010, 0b10111111])

        bs = bits.BitStream( bytearray() )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        bs.write( 0b10101010101010, 14 )
        bs.write( 0b111111, 6 )
        self.assertEqual( target, bs.buffer )

        bs = bits.BitStream( bytearray(), io_endian='little' )
        bs.write( 0b001, 3 )
        bs.write( 0b001, 3 )
        bs.write( 0b001, 3 )
        bs.write( 0b001, 3 )
        bs.write( 0b01010101010101, 14 )
        bs.write( 0b111111, 6 )
        self.assertEqual( target, bs.buffer )

        bs = bits.BitStream( bytearray(), bytes_reverse=True )
        bs.write( 0b10111111101010100, 17 )
        bs.write( 0b100, 3 )
        bs.write( 0b1010, 4 )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        bs.write( 0b10, 2 )
        self.assertEqual( target, bs.buffer )

        bs = bits.BitStream( bytearray(), bytes_reverse=True, io_endian='little', bit_endian='little' )
        bs.write( 0b111111, 6 )
        bs.write( 0b10101010101010, 14 )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        bs.write( 0b100, 3 )
        self.assertEqual( target, bs.buffer )

    def test_bits_seek( self ):
        target = bytes([0b10010010, 0b01001010, 0b10101010, 0b10111111])
        bs = bits.BitStream( target )

        bs.seek( (3, 4) )
        self.assertEqual( bs.tell(), (3, 4) )
        bs.seek( (1, 2) )
        self.assertEqual( bs.tell(), (1, 2) )
        bs.seek( (1, 2), origin='current' )
        self.assertEqual( bs.tell(), (2, 4) )
        bs.seek( (-1, -4), origin='current' )
        self.assertEqual( bs.tell(), (1, 0) )
        bs.seek( (-1, -2), origin='end' )
        self.assertEqual( bs.tell(), (2, 6) )



class TestSound( unittest.TestCase ):

    def test_resampling( self ):
        source = b'\x80' * sound.RESAMPLE_BUFFER + b'\x00' * sound.RESAMPLE_BUFFER


if __name__ == '__main__':
    unittest.main()
