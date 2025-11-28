import math

from mrcrowbar import models as mrc


class WFNChar( mrc.Block ):
    width = mrc.UInt16_LE()
    height = mrc.UInt16_LE()
    
    @property
    def data_size(self):
        return math.ceil(self.width/8)*self.height

    data = mrc.Bytes(length=mrc.Ref("data_size"))


class WFN( mrc.Block ):
    sig = mrc.Const(mrc.Bytes(length=15), b"WGT Font File  ")
    table_addr = mrc.UInt16_LE()

    @property
    def total_char_data(self) -> int:
        return self.table_addr - self.get_field_end_offset("table_addr")

    @total_char_data.setter
    def total_char_data(self, value: int) -> None:
        self.table_addr = value + self.get_field_end_offset("table_addr")


    raw_data = mrc.Bytes(length=mrc.Ref("total_char_data"))
    table = mrc.UInt16_LE(stream=True)

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chars = mrc.LinearStore(
                parent=self,
                source=mrc.Ref("raw_data"),
                block_klass=WFNChar,
                offsets=mrc.Ref("table"),
                base_offset=mrc.EndOffset("table_addr", neg=True),
        )
