#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os, struct, sys
import decrypto
from constants import BAR_LENGTH, BOOK_MOBI, TEXTREAD, ENCODING, UTF8

class MobiBook(object):

    def __init__(self, path, format):
        self.__path = path
        self.__format = format
        self.__sections = []
        self.__exth_record = {} 
        self.__extra_data_flags = 0

        rf = open(self.__path, mode='rb')
        size = os.path.getsize(self.__path)
        data = rf.read(size)
        rf.close()
        
        self.__data = data
        self.__num, = struct.unpack('>H', data[76:78])

        for i in range(self.__num):
            offset, a1,a2,a3,a4 = struct.unpack('>LBBBB', data[78+i*8:78+i*8+8])
            flags, val = a1, a2<<16|a3<<8|a4
            self.__sections.append((offset, flags, val))

        self.__sect = self.__load_section(0)

        # parse info from section[0]
        self.__records, = struct.unpack('>H', self.__sect[0x8:0x8+2])
        compression, = struct.unpack('>H', self.__sect[0x0:0x0+2])
        self.__mobi_header_len, = struct.unpack('>L', self.__sect[0x14:0x18])
        # mobi_codepage, = struct.unpack('>L', self.__sect[0x1C:0x20])
        self.__mobi_version, = struct.unpack('>L', self.__sect[0x68:0x6C])
        
        print("MOBI header version = %d, length = %d" % (self.__mobi_version, self.__mobi_header_len))

        if self.__mobi_header_len >= 0xE4 and self.__mobi_version >= 5:
            self.__extra_data_flags, = struct.unpack('>H', self.__sect[0xF2:0xF4])
        
        if compression != 17480:
            self.__extra_data_flags &= 0xFFFE

        exth_flag, = struct.unpack('>I', self.__sect[0x80:0x84])
        exth = None
        if exth_flag & 0x40: # bit6
            print("There's an EXTH record!")
            # The EXTH header follows immediately after the MOBI header.
            exth = self.__sect[16 + self.__mobi_header_len:]

        # exth[0:4] is the EXTH identifier
        if (len(exth) >= 4) and (exth[0:4].decode(ENCODING) == 'EXTH'):
            # The number of records in the EXTH header.
            nitems, = struct.unpack('>I', exth[8:12])
            # EXTH record start 
            pos = 12
            for i in range(nitems):
                type, size = struct.unpack('>2I', exth[pos:pos + 8])
                content = exth[pos + 8:pos + size]
                self.__exth_record[type] = content
                if type == 401 and  size == 9: # clippinglimit : nteger percentage of the text allowed to be clipped. Usually 10.
                    self.__patch_section(0, "\144", 16 + self.__mobi_header_len + pos + 8)
                elif type == 404 and size == 9: # ttsflag
                    self.__patch_section(0, "\0", 16 + self.__mobi_header_len + pos + 8)
                pos += size

    def __load_section(self, section):
        if (section + 1 == self.__num):
            endoff = len(self.__data)
        else:
            endoff = self.__sections[section + 1][0]

        off = self.__sections[section][0]
        return self.__data[off:endoff]

    def __patch_section(self, section, new, in_off = 0):
        if (section + 1 == self.__num):
            endoff = len(self.__data)
        else:
            endoff = self.__sections[section + 1][0]

        off = self.__sections[section][0]
        assert off + in_off + len(new) <= endoff

        self.__patch(off + in_off, new)
    
    def __patch(self, off, new):
        self.__data = self.__data[:off] + bytes(new, ENCODING) + self.__data[off+len(new):]

    def get_book_title(self):
        title = ''
        if self.__format == BOOK_MOBI:
            if 503 in self.__exth_record:
                title = self.__exth_record[503]
            else:
                toff, tlen = struct.unpack('>2I', self.__sect[0x54:0x5c])
                tend = toff + tlen
                title = self.__sect[toff:tend]

        if title == '':
            _, temp = os.path.split(self.__path)
            title = temp.split(".")[0]
            return title
          
        return title.decode(UTF8)

    def __get_pid_meta_info(self):
        tamper_proof_key = ''
        token = ''
        if 209 in self.__exth_record:
            # It is used by the Kindle for generating book-specific PIDs.
            tamper_proof_key = self.__exth_record[209]
            data = tamper_proof_key
            length = len(data)
            #The 209 data comes in five byte groups.
            #Interpret the last four bytes of each group 
            #as a big endian unsigned integer to get a key value
            #if that key exists in the exth_record,
            #append its contents to the token    
            for i in range(length):
                if i+5 <= length:
                    val, = struct.unpack('>I', data[i+1:i+5])
                    sval = self.__exth_record.get(val, '')
                    if isinstance(sval, str):
                        token += sval
                    else:
                        token += sval.decode(ENCODING)
        return tamper_proof_key, token

    def process_book(self, serial):
        # Only type 0, 1, 2 are valid.
        crypto_type, = struct.unpack('>H', self.__sect[0xC:0xC+2])
        if crypto_type == 0:
            print("This book is not encrypted!")
            return False

        if not crypto_type in (1, 2):
            print("Unknown encryption type:%d" % crypto_type)
            return False

        if 406 in self.__exth_record:
            rent_expiration_date, = struct.unpack('>Q', self.__exth_record[406])
            if rent_expiration_date != 0:
                print("Cannot decode library or rented ebooks!")
                return False

        pid = '00000000'
        book_key_data = None
        found_key = ''

        if crypto_type == 1:
            print("Old Mobipocket Encryptioin")
            t1_keyvec = "QDCVEPMU675RUBSZ"
            if self.__format == TEXTREAD:
                book_key_data = self.__sect[0x0E:0x0E+16]
            elif self.__mobi_version < 0:
                book_key_data = self.__sect[0x90:0x90+16]
            else:
                book_key_data = self.__sect[self.__mobi_header_len+16:self.__mobi_header_len+32]
            
            found_key = decrypto.PC1(t1_keyvec, book_key_data)
            
            print("File has default encryption, no specific PID.")
        else: # crypto_type == 2
            print("Mobipocket Encryption")
        
            md1, md2 = self.__get_pid_meta_info()
            pid = decrypto.get_kindle_pid(md1, md2, serial)

            if len(pid) != 8:
                print("Error: PID %s is incorrect." % pid)
                return False

            print("File is encoded with PID %s." % pid)

            # drm_offset : offset to DRM key info in DRMed file.
            #                0xffffffff if no DRM
            # drm_count : numbers of entries in DRM info. 
               #                0xffffffff if no DRM 
            # drm_size : Numbers of bytes in DRM info
            # _(ignore) : Some flags concerning the DRM info
            # calculate the keys
            drm_offset, drm_count, drm_size, _ = struct.unpack('>LLLL', self.__sect[0xA8:0xA8+16])
            if drm_count == 0:
                print("No PIDs found in this file")
                return False
            
            found_key = self.__parse_drm(self.__sect[drm_offset:drm_offset+drm_size], drm_count, pid)
            if found_key == '':
                print("No key found. maybe the PID is incorrect")
                return False

            # kill the drm keys
            self.__patch_section(0, "\0" * drm_size, drm_offset)            
            # kill the drm pointers
            self.__patch_section(0, "\xff" * 4 + "\0" * 12, 0xA8)

        # clear the crypto type
        self.__patch_section(0, "\0" * 2, 0xC)

        # decrypt sections
        print("Decrypting. Please wait ...")

        new_data = self.__data[0:self.__sections[1][0]]

        for i in range(1, self.__records+1):
            data = self.__load_section(i)
            ptr = data.decode(ENCODING)
            extra_size = decrypto.get_size_of_trailing_data_entries(ptr, len(data), self.__extra_data_flags)

            # progress bar
            percent = i / self.__records
            hashes = '#' * int(percent * BAR_LENGTH)
            spaces = ' ' * (BAR_LENGTH - len(hashes))
            sys.stdout.write("\rPercent: [%s] %d%%" % (hashes + spaces, percent*100))
            sys.stdout.flush()

            pc_data = decrypto.PC1(found_key, data[0:len(data) - extra_size])
            new_data += bytes(pc_data, ENCODING)

            if extra_size > 0:
                new_data += data[-extra_size:]

        print() # new line

        if self.__num > self.__records+1:
            new_data += self.__data[self.__sections[self.__records+1][0]:]

        self.__data = new_data
        return True

    def __parse_drm(self, data, count, pid):
        keyvec1 = "\x72\x38\x33\xB0\xB4\xF2\xE3\xCA\xDF\x09\x01\xD6\xE2\xE0\x3F\x96"
        #keyascii = [114, 56, 51, 176, 180, 242, 227, 202, 223, 9, 1, 214, 226, 224, 63, 150]
        pid = pid.ljust(16,'\0')
        temp_key = decrypto.PC1(keyvec1, pid, False)
        temp_key_sum = sum(map(ord, temp_key)) & 0xff

        found_key = None
        for i in range(count):
            verification, _, _, cksum, cookie = struct.unpack('>LLLBxxx32s', data[i*0x30:i*0x30+0x30])
            cookie = decrypto.PC1(temp_key, cookie)

            ver, flags = struct.unpack('>LL', bytes(cookie[0:8], ENCODING))
            finalkey = cookie[8:24]

            if verification == ver and cksum == temp_key_sum and (flags & 0x1F) == 1:
                found_key = finalkey
                break

        if not found_key:
            # Then try the default encoding that doesn't require a PID
            temp_key = keyvec1
            temp_key_sum = sum(map(ord, temp_key)) & 0xff
            for i in range(count):
                verification, _, _, cksum, cookie = struct.unpack('>LLLBxxx32s', data[i*0x30:i*0x30+0x30])
                cookie = decrypto.PC1(temp_key, cookie)

                ver, _ = struct.unpack('>LL', bytes(cookie[0:8], ENCODING))
                finalkey = cookie[8:24]

                if verification == ver and cksum == temp_key_sum:
                    found_key = finalkey
                    break
                
        return found_key

    def get_result(self):
        return self.__data