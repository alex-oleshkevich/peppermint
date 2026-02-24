import typing

from peppermint import descriptors
from peppermint.config import configure
from peppermint.factories import Factory

T = typing.TypeVar("T")


gen = descriptors._Gen
seq = descriptors.SequenceDescriptor
call = descriptors.CallDescriptor
lazy = descriptors.LazyDescriptor
seq = descriptors.SequenceDescriptor
sub = descriptors.SubFactoryDescriptor
sub_list = descriptors.SubListFactoryDescriptor
ignore = descriptors.IgnoreDescriptor


__all__ = [
    "Factory",
    "call",
    "configure",
    "gen",
    "ignore",
    "lazy",
    "seq",
    "sub",
    "sub_list",
]
