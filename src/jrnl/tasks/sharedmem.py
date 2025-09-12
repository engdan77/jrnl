from typing import Union
from loguru import logger

from shared_memory_dict import SharedMemoryDict

share_mem_pointer: Union[SharedMemoryDict | None] = None


def create_shared():
    global share_mem_pointer
    share_mem_pointer = SharedMemoryDict(name='shared', size=16)


def set_shared(value):
    global share_mem_pointer
    share_mem_pointer['value'] = value


def get_shared():
    global share_mem_pointer
    logger.debug(f'Getting shared memory pointer: {share_mem_pointer}')
    return share_mem_pointer['value']


def close_shared():
    # logger.debug('Closing shared memory')
    global share_mem_pointer
    if share_mem_pointer is not None:
        share_mem_pointer.shm.close()
        try:
            share_mem_pointer.shm.unlink()
        except FileNotFoundError:
            pass
