# Manually written with reference to:
# http://www.aps.anl.gov/epics/base/R3-16/0-docs/CAproto/index.html#payload-data-types
# https://github.com/epics-base/epics-base/blob/813166128eae1240cdd643869808abe1c4621321/src/ca/client/db_access.h

# The organizational code, making use of Enum, comes from pypvasync by Kenneth
# Lauer.

import array
import ctypes
import datetime
from enum import IntEnum

try:
    import numpy
except ImportError:
    USE_NUMPY = False
else:
    USE_NUMPY = True

EPICS2UNIX_EPOCH = 631152000.0
EPICS_EPOCH = datetime.datetime.utcfromtimestamp(EPICS2UNIX_EPOCH)

MAX_STRING_SIZE = 40
MAX_UNITS_SIZE = 8
MAX_ENUM_STRING_SIZE = 26
MAX_ENUM_STATES = 16

DO_REPLY = 10
NO_REPLY = 5


class AccessRights(IntEnum):
    NO_ACCESS = 0
    READ = 1
    WRITE = 2
    READ_WRITE = 3


class AlarmSeverity(IntEnum):
    NO_ALARM = 0
    MINOR_ALARM = 1
    MAJOR_ALARM = 2
    INVALID_ALARM = 3


class AlarmStatus(IntEnum):
    NO_ALARM = 0
    READ = 1
    WRITE = 2
    HIHI = 3
    HIGH = 4
    LOLO = 5
    LOW = 6
    STATE = 7
    COS = 8
    COMM = 9
    TIMEOUT = 10
    HWLIMIT = 11
    CALC = 12
    SCAN = 13
    LINK = 14
    SOFT = 15
    BAD_SUB = 16
    UDF = 17
    DISABLE = 18
    SIMM = 19
    READ_ACCESS = 20
    WRITE_ACCESS = 21


# EPICS Constants
class ECA(IntEnum):
    NORMAL = 1
    TIMEOUT = 80
    IODONE = 339
    ISATTACHED = 424
    BADCHID = 410


class ConnStatus(IntEnum):
    CS_CONN = 2
    OP_CONN_UP = 6
    OP_CONN_DOWN = 7
    CS_NEVER_SEARCH = 4


class ChannelType(IntEnum):
    STRING = 0
    INT = 1
    SHORT = 1
    FLOAT = 2
    ENUM = 3
    CHAR = 4
    LONG = 5
    DOUBLE = 6

    STS_STRING = 7
    STS_SHORT = 8
    STS_INT = 8
    STS_FLOAT = 9
    STS_ENUM = 10
    STS_CHAR = 11
    STS_LONG = 12
    STS_DOUBLE = 13

    TIME_STRING = 14
    TIME_INT = 15
    TIME_SHORT = 15
    TIME_FLOAT = 16
    TIME_ENUM = 17
    TIME_CHAR = 18
    TIME_LONG = 19
    TIME_DOUBLE = 20

    GR_STRING = 21  # not implemented by EPICS
    GR_SHORT = 22
    GR_INT = GR_SHORT
    GR_FLOAT = 23
    GR_ENUM = 24
    GR_CHAR = 25
    GR_LONG = 26
    GR_DOUBLE = 27

    CTRL_STRING = 28  # not implemented by EPICS
    CTRL_INT = 29
    CTRL_SHORT = 29
    CTRL_FLOAT = 30
    CTRL_ENUM = 31
    CTRL_CHAR = 32
    CTRL_LONG = 33
    CTRL_DOUBLE = 34

    PUT_ACKT = 35
    PUT_ACKS = 36

    STSACK_STRING = 37
    CLASS_NAME = 38


class SubscriptionType(IntEnum):
    '''Subscription masks

    DBE_VALUE
    Trigger an event when a significant change in the channel's value occurs.
    (in epics-base, relies on the monitor deadband field under DCT.)

    DBE_ARCHIVE (DBE_LOG)
    Trigger an event when an archive significant change in the channel's valuue
    occurs.
    (in epics-base, relies on the archiver monitor deadband field under DCT.)

    DBE_ALARM
    Trigger an event when the alarm state changes

    DBE_PROPERTY
    Trigger an event when a property change (control limit, graphical limit,
    status string, enum string ...) occurs.
    '''

    DBE_VALUE = 1
    DBE_LOG = 2
    DBE_ALARM = 4
    DBE_PROPERTY = 8


ChType = ChannelType


string_t = MAX_STRING_SIZE * ctypes.c_char  # epicsOldString
char_t = ctypes.c_char  # epicsUint8
short_t = ctypes.c_int16  # epicsInt16
ushort_t = ctypes.c_uint16  # epicsUInt16
int_t = ctypes.c_int16  # epicsInt16
long_t = ctypes.c_int32  # epicsInt32
ulong_t = ctypes.c_uint32  # epicsUInt32
float_t = ctypes.c_float  # epicsFloat32
double_t = ctypes.c_double  # epicsFloat64


def epics_timestamp_to_unix(seconds_since_epoch, nano_seconds):
    '''UNIX timestamp (seconds) from Epics TimeStamp structure'''
    return (EPICS2UNIX_EPOCH + seconds_since_epoch + 1.e-6 *
            int(1.e-3 * nano_seconds))


def timestamp_to_epics(ts):
    '''Python timestamp from EPICS TimeStamp structure'''
    if isinstance(ts, float):
        ts = datetime.datetime.utcfromtimestamp(ts)
    dt = ts - EPICS_EPOCH
    return int(dt.total_seconds()), int(dt.microseconds * 1e3)


class DbrTypeBase(ctypes.BigEndianStructure):
    _pack_ = 1
    info_fields = ()

    def to_dict(self):
        return {field: getattr(self, field)
                for field in self.info_fields}


class TimeStamp(DbrTypeBase):
    "emulate epics timestamp"
    _fields_ = [('secondsSinceEpoch', ctypes.c_uint32),
                ('nanoSeconds', ctypes.c_uint32)]

    info_fields = ('timestamp', )

    @property
    def timestamp(self):
        "UNIX timestamp (seconds) from Epics TimeStamp structure"
        return epics_timestamp_to_unix(self.secondsSinceEpoch,
                                       self.nanoSeconds)


class TimeTypeBase(DbrTypeBase):
    # access to secondsSinceEpoch and nanoSeconds:
    _anonymous_ = ('stamp', )
    _fields_ = [('status', short_t),
                ('severity', short_t),
                ('stamp', TimeStamp)
                ]
    info_fields = ('status', 'severity', 'timestamp')

    @property
    def timestamp(self):
        '''Unix timestamp'''
        return self.stamp.timestamp


class StatusTypeBase(DbrTypeBase):
    info_fields = ('status', 'severity', )
    _fields_ = [('status', short_t),
                ('severity', short_t)
                ]


class GraphicControlBase(DbrTypeBase):
    graphic_fields = ('upper_disp_limit', 'lower_disp_limit',
                      'upper_alarm_limit', 'upper_warning_limit',
                      'lower_warning_limit', 'lower_alarm_limit')
    control_fields = ('upper_ctrl_limit', 'lower_ctrl_limit')
    info_fields = ('status', 'severity', ) + graphic_fields
    _fields_ = [('status', short_t),
                ('severity', short_t)
                ]

    @classmethod
    def build_control_fields(cls, type_):
        return [(field, type_) for field in
                cls.graphic_fields + cls.control_fields]

    @classmethod
    def build_graphic_fields(cls, type_):
        return [(field, type_) for field in cls.graphic_fields]


class GraphicControlUnits(GraphicControlBase):
    _fields_ = [('units', char_t * MAX_UNITS_SIZE),
                ]


class ControlTypeUnits(GraphicControlUnits):
    info_fields = (GraphicControlBase.info_fields +
                   GraphicControlBase.control_fields + ('units', ))


class GraphicTypeUnits(GraphicControlUnits):
    info_fields = GraphicControlBase.info_fields + ('units', )


class GraphicControlPrecision(GraphicControlBase):
    _fields_ = [('precision', short_t),
                ('RISC_pad0', short_t),
                ('units', char_t * MAX_UNITS_SIZE),
                ]


class ControlTypePrecision(GraphicControlPrecision):
    info_fields = (GraphicControlBase.info_fields +
                   GraphicControlBase.control_fields +
                   ('precision', 'units', ))


class GraphicTypePrecision(GraphicControlPrecision):
    info_fields = (GraphicControlBase.info_fields +
                   ('precision', 'units', ))


class DbrValueType(DbrTypeBase):
    info_fields = ('value', )


class DBR_STRING(DbrValueType):
    DBR_ID = ChannelType.STRING
    _fields_ = [('value', string_t)]


class DBR_INT(DbrValueType):
    DBR_ID = ChannelType.INT
    _fields_ = [('value', int_t)]


class DBR_FLOAT(DbrValueType):
    DBR_ID = ChannelType.FLOAT
    _fields_ = [('value', float_t)]


class DBR_ENUM(DbrValueType):
    DBR_ID = ChannelType.ENUM
    _fields_ = [('value', ushort_t)]


class DBR_CHAR(DbrValueType):
    DBR_ID = ChannelType.CHAR
    _fields_ = [('value', char_t)]


class DBR_LONG(DbrValueType):
    DBR_ID = ChannelType.LONG
    _fields_ = [('value', long_t)]


class DBR_DOUBLE(DbrValueType):
    DBR_ID = ChannelType.DOUBLE
    _fields_ = [('value', double_t)]


class DBR_STS_STRING(StatusTypeBase):
    DBR_ID = ChannelType.STS_STRING


class DBR_STS_INT(StatusTypeBase):
    DBR_ID = ChannelType.STS_SHORT


class DBR_STS_FLOAT(StatusTypeBase):
    DBR_ID = ChannelType.STS_FLOAT


class DBR_STS_ENUM(StatusTypeBase):
    DBR_ID = ChannelType.STS_ENUM


class DBR_STS_CHAR(StatusTypeBase):
    DBR_ID = ChannelType.STS_CHAR
    _fields_ = [
        ('RISC_pad', char_t),
    ]


class DBR_STS_LONG(StatusTypeBase):
    DBR_ID = ChannelType.STS_LONG


class DBR_STS_DOUBLE(StatusTypeBase):
    DBR_ID = ChannelType.STS_DOUBLE
    _fields_ = [
        ('RISC_pad', long_t),
    ]


class DBR_TIME_STRING(TimeTypeBase):
    DBR_ID = ChannelType.TIME_STRING
    _fields_ = []


class DBR_TIME_INT(TimeTypeBase):
    DBR_ID = ChannelType.TIME_INT
    _fields_ = [
        ('RISC_pad', short_t),
    ]


class DBR_TIME_FLOAT(TimeTypeBase):
    DBR_ID = ChannelType.TIME_FLOAT
    _fields_ = []


class DBR_TIME_ENUM(TimeTypeBase):
    DBR_ID = ChannelType.TIME_ENUM
    _fields_ = [
        ('RISC_pad', short_t),
    ]


class DBR_TIME_CHAR(TimeTypeBase):
    DBR_ID = ChannelType.TIME_CHAR
    _fields_ = [
        ('RISC_pad0', short_t),
        ('RISC_pad1', char_t),
    ]


class DBR_TIME_LONG(TimeTypeBase):
    DBR_ID = ChannelType.TIME_LONG
    _fields_ = []


class DBR_TIME_DOUBLE(TimeTypeBase):
    DBR_ID = ChannelType.TIME_DOUBLE
    _fields_ = [
        ('RISC_pad', long_t),
    ]


# DBR_GR_STRING (21) is not implemented by EPICS. - use DBR_STS_STRING


class DBR_GR_INT(GraphicTypeUnits):
    DBR_ID = ChannelType.GR_SHORT
    _fields_ = GraphicTypeUnits.build_graphic_fields(short_t)


class DBR_GR_FLOAT(GraphicTypePrecision):
    DBR_ID = ChannelType.GR_FLOAT
    _fields_ = GraphicTypeUnits.build_graphic_fields(float_t)


class DBR_GR_ENUM(GraphicControlBase):
    DBR_ID = ChannelType.GR_ENUM
    graphic_fields = ()
    control_fields = ()
    info_fields = ('status', 'severity', 'enum_strs', )
    _fields_ = [
        ('no_str', short_t),  # number of strings
        ('strs', MAX_ENUM_STATES * (MAX_ENUM_STRING_SIZE * char_t)),
    ]

    @property
    def enum_strs(self):
        '''Enum byte strings as a tuple'''
        return tuple(self.strs[i].value
                     for i in range(self.no_str))



class DBR_GR_CHAR(GraphicTypeUnits):
    DBR_ID = ChannelType.GR_CHAR
    _fields_ = (GraphicTypeUnits.build_graphic_fields(char_t) +
                [('RISC_pad', char_t)])


class DBR_GR_LONG(GraphicTypeUnits):
    DBR_ID = ChannelType.GR_LONG
    _fields_ = GraphicTypeUnits.build_graphic_fields(long_t)


class DBR_GR_DOUBLE(GraphicTypePrecision):
    DBR_ID = ChannelType.GR_DOUBLE
    _fields_ = GraphicTypePrecision.build_graphic_fields(double_t)


# DBR_CTRL_STRING (28) is not implemented by libca.

class DBR_CTRL_INT(ControlTypeUnits):
    DBR_ID = ChannelType.CTRL_INT
    _fields_ = ControlTypeUnits.build_control_fields(short_t)


class DBR_CTRL_FLOAT(ControlTypePrecision):
    DBR_ID = ChannelType.CTRL_FLOAT
    _fields_ = ControlTypePrecision.build_control_fields(float_t)


class DBR_CTRL_ENUM(GraphicControlBase):
    DBR_ID = ChannelType.CTRL_ENUM
    control_fields = ()
    graphic_fields = ()
    info_fields = ('status', 'severity', 'enum_strs', )

    _fields_ = [('no_str', short_t),
                ('strs', (char_t * MAX_ENUM_STRING_SIZE) * MAX_ENUM_STATES),
                ]

    @property
    def enum_strs(self):
        '''Enum byte strings as a tuple'''
        return tuple(self.strs[i].value
                     for i in range(self.no_str))


class DBR_CTRL_CHAR(ControlTypeUnits):
    DBR_ID = ChannelType.CTRL_CHAR
    _fields_ = (ControlTypeUnits.build_control_fields(char_t) +
                [('RISC_pad', char_t)])


class DBR_CTRL_LONG(ControlTypeUnits):
    DBR_ID = ChannelType.CTRL_LONG
    _fields_ = ControlTypeUnits.build_control_fields(long_t)


class DBR_CTRL_DOUBLE(ControlTypePrecision):
    DBR_ID = ChannelType.CTRL_DOUBLE
    _fields_ = ControlTypePrecision.build_control_fields(double_t)


class DbrSpecialType(DbrTypeBase):
    ...


class DBR_PUT_ACKT(DbrSpecialType):
    DBR_ID = ChannelType.PUT_ACKT
    info_fields = ('value', )
    _fields_ = [('value', ushort_t)]


class DBR_PUT_ACKS(DbrSpecialType):
    DBR_ID = ChannelType.PUT_ACKS
    info_fields = ('value', )
    _fields_ = [('value', ushort_t)]


class DBR_STSACK_STRING(DbrSpecialType):
    DBR_ID = ChannelType.STSACK_STRING
    info_fields = ('status', 'severity', 'ackt', 'acks', 'value')
    _fields_ = [
        ('status', short_t),
        ('severity', short_t),
        ('ackt', ushort_t),
        ('acks', ushort_t),
        ('value', string_t),
    ]


class DBR_CLASS_NAME(DbrSpecialType):
    DBR_ID = ChannelType.CLASS_NAME
    info_fields = ('value', )
    _fields_ = [('value', string_t)]


DBR_SHORT = DBR_INT
DBR_STS_SHORT = DBR_STS_INT
DBR_TIME_SHORT = DBR_TIME_INT
DBR_GR_SHORT = DBR_GR_INT
DBR_CTRL_SHORT = DBR_CTRL_INT

# ChannelTypes grouped by included metadata
native_types = (ChType.STRING, ChType.INT, ChType.SHORT, ChType.FLOAT,
                ChType.ENUM, ChType.CHAR, ChType.LONG, ChType.DOUBLE)

status_types = (ChType.STS_STRING, ChType.STS_SHORT, ChType.STS_INT,
                ChType.STS_FLOAT, ChType.STS_ENUM, ChType.STS_CHAR,
                ChType.STS_LONG, ChType.STS_DOUBLE)

time_types = (ChType.TIME_STRING, ChType.TIME_INT, ChType.TIME_SHORT,
              ChType.TIME_FLOAT, ChType.TIME_ENUM, ChType.TIME_CHAR,
              ChType.TIME_LONG, ChType.TIME_DOUBLE)

graphical_types = (ChType.GR_STRING, ChType.GR_SHORT, ChType.GR_INT,
                   ChType.GR_FLOAT, ChType.GR_ENUM, ChType.GR_CHAR,
                   ChType.GR_LONG, ChType.GR_DOUBLE)

control_types = (ChType.CTRL_STRING, ChType.CTRL_INT, ChType.CTRL_SHORT,
                 ChType.CTRL_FLOAT, ChType.CTRL_ENUM, ChType.CTRL_CHAR,
                 ChType.CTRL_LONG, ChType.CTRL_DOUBLE)

# ChannelTypes grouped by value data type
char_types = (ChType.CHAR, ChType.TIME_CHAR,
              ChType.CTRL_CHAR, ChType.STS_CHAR)

string_types = (ChType.STRING, ChType.TIME_STRING,
                ChType.CTRL_STRING, ChType.STS_STRING)

int_types = (ChType.INT, ChType.TIME_INT,
             ChType.CTRL_INT, ChType.CTRL_INT,
             ChType.LONG, ChType.TIME_LONG,
             ChType.CTRL_LONG, ChType.CTRL_LONG)

float_types = (ChType.FLOAT, ChType.TIME_FLOAT,
               ChType.CTRL_FLOAT, ChType.CTRL_FLOAT,
               ChType.DOUBLE, ChType.TIME_DOUBLE,
               ChType.CTRL_DOUBLE, ChType.CTRL_DOUBLE)

enum_types = (ChType.ENUM, ChType.STS_ENUM, ChType.TIME_ENUM, ChType.CTRL_ENUM)
char_types = (ChType.CHAR, ChType.TIME_CHAR, ChType.CTRL_CHAR)
native_float_types = (ChType.FLOAT, ChType.DOUBLE)
native_int_types = (ChType.INT, ChType.CHAR, ChType.LONG, ChType.ENUM)

# map of Epics DBR types to ctypes types
DBR_TYPES = {
    ChType.STRING: string_t,
    ChType.INT: int_t,
    ChType.SHORT: int_t,
    ChType.FLOAT: float_t,
    ChType.ENUM: ushort_t,
    ChType.CHAR: char_t,
    ChType.LONG: ulong_t,
    ChType.DOUBLE: double_t,

    ChType.GR_STRING: DBR_STS_STRING,
    ChType.GR_INT: DBR_GR_INT,
    ChType.GR_FLOAT: DBR_GR_FLOAT,
    ChType.GR_ENUM: DBR_GR_ENUM,
    ChType.GR_CHAR: DBR_GR_CHAR,
    ChType.GR_LONG: DBR_GR_LONG,
    ChType.GR_DOUBLE: DBR_GR_DOUBLE,

    ChType.STS_STRING: DBR_STS_STRING,
    ChType.STS_INT: DBR_STS_INT,
    ChType.STS_FLOAT: DBR_STS_FLOAT,
    ChType.STS_ENUM: DBR_STS_ENUM,
    ChType.STS_CHAR: DBR_STS_CHAR,
    ChType.STS_LONG: DBR_STS_LONG,
    ChType.STS_DOUBLE: DBR_STS_DOUBLE,

    ChType.TIME_STRING: DBR_TIME_STRING,
    ChType.TIME_INT: DBR_TIME_INT,
    ChType.TIME_SHORT: DBR_TIME_INT,
    ChType.TIME_FLOAT: DBR_TIME_FLOAT,
    ChType.TIME_ENUM: DBR_TIME_ENUM,
    ChType.TIME_CHAR: DBR_TIME_CHAR,
    ChType.TIME_LONG: DBR_TIME_LONG,
    ChType.TIME_DOUBLE: DBR_TIME_DOUBLE,

    # Note: there is no ctrl string in the C definition
    ChType.CTRL_STRING: DBR_STS_STRING,
    ChType.CTRL_SHORT: DBR_CTRL_INT,
    ChType.CTRL_INT: DBR_CTRL_INT,
    ChType.CTRL_FLOAT: DBR_CTRL_FLOAT,
    ChType.CTRL_ENUM: DBR_CTRL_ENUM,
    ChType.CTRL_CHAR: DBR_CTRL_CHAR,
    ChType.CTRL_LONG: DBR_CTRL_LONG,
    ChType.CTRL_DOUBLE: DBR_CTRL_DOUBLE,

    # Special types:
    ChType.STSACK_STRING: DBR_STSACK_STRING,
    ChType.CLASS_NAME: DBR_CLASS_NAME,

}

if USE_NUMPY:
    _numpy_map = {
        ch_type: numpy.dtype(dtype).newbyteorder('>')
        for ch_type, dtype in
        [(ChType.INT, numpy.int16),
         (ChType.FLOAT, numpy.float32),
         (ChType.ENUM, numpy.uint16),
         (ChType.CHAR, numpy.uint8),
         (ChType.LONG, numpy.int32),
         (ChType.DOUBLE, numpy.float64),
         (ChType.STRING, '>S40'),
         (ChType.CHAR, 'b'),
         (ChType.STSACK_STRING, numpy.uint8),
         (ChType.CLASS_NAME, numpy.uint8),
         ]
    }


_array_type_code_map = {
    ChType.STRING: 'B',  # TO DO
    ChType.INT: 'h',
    ChType.FLOAT: 'f',
    ChType.ENUM: 'H',
    ChType.CHAR: 'b',
    ChType.LONG: 'i',
    ChType.DOUBLE: 'd',

    ChType.STSACK_STRING: 'b',
    ChType.CLASS_NAME: 'b',
}

for _type in set(native_types) - set([ChType.STRING]):
    assert (array.array(_array_type_code_map[_type]).itemsize ==
            ctypes.sizeof(DBR_TYPES[_type])), '{!r} check failed'.format(_type)

del _type

# Offset of the data in bytes, according to the DBR type
dbr_data_offsets = {
    data_type: ctypes.sizeof(DBR_TYPES[data_type])
    if data_type not in native_types
    else 0
    for data_type in DBR_TYPES
}


def array_type_code(native_type):
    return _array_type_code_map[native_type]


_native_map = {
    ChType.STRING: ChType.STRING,
    ChType.INT: ChType.INT,
    ChType.FLOAT: ChType.FLOAT,
    ChType.ENUM: ChType.ENUM,
    ChType.CHAR: ChType.CHAR,
    ChType.LONG: ChType.LONG,
    ChType.DOUBLE: ChType.DOUBLE,

    ChType.STS_STRING: ChType.STRING,
    ChType.STS_INT: ChType.INT,
    ChType.STS_FLOAT: ChType.FLOAT,
    ChType.STS_ENUM: ChType.ENUM,
    ChType.STS_CHAR: ChType.CHAR,
    ChType.STS_LONG: ChType.LONG,
    ChType.STS_DOUBLE: ChType.DOUBLE,

    ChType.TIME_STRING: ChType.STRING,
    ChType.TIME_INT: ChType.INT,
    ChType.TIME_SHORT: ChType.SHORT,
    ChType.TIME_FLOAT: ChType.FLOAT,
    ChType.TIME_ENUM: ChType.ENUM,
    ChType.TIME_CHAR: ChType.CHAR,
    ChType.TIME_LONG: ChType.LONG,
    ChType.TIME_DOUBLE: ChType.DOUBLE,

    ChType.GR_STRING: ChType.STRING,
    ChType.GR_INT: ChType.INT,
    ChType.GR_SHORT: ChType.SHORT,
    ChType.GR_FLOAT: ChType.FLOAT,
    ChType.GR_ENUM: ChType.ENUM,
    ChType.GR_CHAR: ChType.CHAR,
    ChType.GR_LONG: ChType.LONG,
    ChType.GR_DOUBLE: ChType.DOUBLE,

    ChType.CTRL_STRING: ChType.STRING,
    ChType.CTRL_SHORT: ChType.SHORT,
    ChType.CTRL_INT: ChType.INT,
    ChType.CTRL_FLOAT: ChType.FLOAT,
    ChType.CTRL_ENUM: ChType.ENUM,
    ChType.CTRL_CHAR: ChType.CHAR,
    ChType.CTRL_LONG: ChType.LONG,
    ChType.CTRL_DOUBLE: ChType.DOUBLE,

    # Special types:
    ChType.STSACK_STRING: ChType.STSACK_STRING,
    ChType.CLASS_NAME: ChType.CLASS_NAME,

}


def native_type(ftype):
    '''return native field type from TIME or CTRL variant'''
    return _native_map[ftype]


def native_to_builtin(value, native_type, data_count):
    # - A waveform of characters is just a bytestring.
    # - A waveform of strings is an array whose elements are fixed-length (40-
    #   character) strings.
    # - Enums are just integers that happen to have special significance.
    # - Everything else is, straightforwardly, an array of numbers.
    if USE_NUMPY:
        # Return an ndarray
        dt = _numpy_map[native_type]
        if native_type == ChType.STRING and len(value) < MAX_STRING_SIZE:
            # caput behaves this way
            return numpy.frombuffer(
                bytes(value).ljust(MAX_STRING_SIZE, b'\x00'), dtype=dt)

        return numpy.frombuffer(value, dtype=dt)
    else:
        # TODO
        return  # array.array()


def promote_type(ftype, *, use_status=False, use_time=False, use_ctrl=False,
                 use_gr=False):
    """Promotes a native field type to its STS, TIME, CTRL, or GR variant.

    Returns
    -------
    ftype : int
        the promoted field value.
    """
    if sum([use_status, use_time, use_ctrl, use_gr]) > 1:
        raise ValueError("Only one of the kwargs may be True.")
    # Demote it back to a native type, if necessary
    ftype = _native_map[ChType(ftype)]

    if ftype in (ChType.STSACK_STRING, ChType.CLASS_NAME):
        return ftype

    # Use the fact that the types are ordered in blocks and that the STRING
    # variant is the first element of each block.
    if use_ctrl:
        ftype += ChType.CTRL_STRING
    elif use_time:
        ftype += ChType.TIME_STRING
    elif use_status:
        ftype += ChType.STS_STRING
    elif use_gr:
        ftype += ChType.GR_STRING

    if ftype == ChType.CTRL_STRING:
        return ChType.TIME_STRING
    return ChType(ftype)
