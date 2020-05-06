#/usr/bin/python
# -*- coding: UTF-8 -*-

import hashlib, struct

from constants import CHAR_MAP3, ENCODING

# Implementation of Pukall Cipher 1
# return str
def PC1(key, src, decryption=True):
    sum1 = 0
    sum2 = 0
    keyXorVal = 0
    if len(key)!=16:
        print("Bad key length!")
        return None
    wkey = []
    for i in range(8):
        wkey.append(ord(key[i*2])<<8 | ord(key[i*2+1]))

    dst = ""
    for i in range(len(src)):
        temp1 = 0
        byteXorVal = 0
        for j in range(8):
            temp1 ^= wkey[j]
            sum2  = (sum2+j)*20021 + sum1
            sum1  = (temp1*346)&0xFFFF
            sum2  = (sum2+sum1)&0xFFFF
            temp1 = (temp1*20021+1)&0xFFFF
            byteXorVal ^= temp1 ^ sum2

        curByte = ord(src[i:i+1])
        if not decryption:
            keyXorVal = curByte * 257
        curByte = ((curByte ^ (byteXorVal >> 8)) ^ byteXorVal) & 0xFF
        if decryption:
            keyXorVal = curByte * 257
        for j in range(8):
            wkey[j] ^= keyXorVal
        dst+=chr(curByte)
    return dst

# Returns two bit at offset from a bit field
def get_two_bits_from_bit_field(bit_field, offset):
    byte_num = int(offset / 4)
    bit_pos = 6 - 2*(offset % 4)
    return bit_field[byte_num] >> bit_pos & 3

# Returns the six bits at offset from a bit field
def get_six_bits_from_bit_field(bit_field, offset):
    offset *= 3
    value = (get_two_bits_from_bit_field(bit_field,offset) <<4) + (get_two_bits_from_bit_field(bit_field,offset+1) << 2) +get_two_bits_from_bit_field(bit_field,offset+2)
    return value

def encode_pid(hash):
    pid = ''
    for position in range(8):
        pid += CHAR_MAP3[get_six_bits_from_bit_field(hash, position)]
    return pid

# Parse the EXTH header records and use the Kindle serial number to calculate the book pid.
def get_kindle_pid(tamper_proof_key, token, serialnum):    
    str = bytes(serialnum, ENCODING) + tamper_proof_key + bytes(token, ENCODING)
    pidhash = hashlib.sha1(str).digest()
    bookpid = encode_pid(pidhash)
    return bookpid

# ptr <class str>
# size <class int>
# flags <class int>
def get_size_of_trailing_data_entries(ptr, size, flags):
    def get_size_of_trailing_data_entry(ptr, size):
        bitpos, result = 0, 0
        if size <= 0:
            return result

        while True:
            v = ord(ptr[size-1])
            result |= (v & 0x7F) << bitpos
            bitpos += 7
            size -= 1
            if (v & 0x80) != 0 or (bitpos >= 28) or (size == 0):
                return result

    num = 0 
    testflags = flags >> 1
    while testflags:
        if testflags & 1:
            num += get_size_of_trailing_data_entry(ptr, size - num)
        testflags >>= 1

    return num