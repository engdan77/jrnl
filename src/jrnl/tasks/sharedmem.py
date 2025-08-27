from typing import Union

from shared_memory_dict import SharedMemoryDict

share_mem_pointer: Union[SharedMemoryDict | None] = None


def set_shared(value):
    shared_mem = SharedMemoryDict(name='shared', size=16)
    shared_mem['value'] = value
    global share_mem_pointer
    if not share_mem_pointer:
        share_mem_pointer = shared_mem


def get_shared():
    global share_mem_pointer
    return share_mem_pointer['value']


def close_shared():
    global share_mem_pointer
    if share_mem_pointer is not None:
        share_mem_pointer.shm.close()
        share_mem_pointer.shm.unlink()
