#!/usr/bin/env python2.7

from collections import namedtuple

import os.path
import struct
import sys


if __name__ == "__main__":
    ei_class = ['Invalid', 'ELF32', 'ELF64']
    ei_version = ['Invalid', 'Current']

    ei_data = [
        'Invalid',
        "2's complement, little endian",
        "2's complement, big endian"
    ]

    os_abi = {
        0: 'UNIX System V',
        1: 'HP-UX',
        2: 'NetBSD',
        3: 'GNU/Linux',
        4: 'GNU/Hurd',
        6: 'Solaris',
        7: 'AIX',
        8: 'IRIX',
        9: 'FreeBSD',
        10: 'TRU64 UNIX',
        11: 'Novell Modesto',
        12: 'OpenBSD',
        13: 'OpenVMS',
        14: 'HP Non-Stop Kernel',
        15: 'Amiga Research OS',
        97: 'ARM',
        255: 'Standalone (embedded)'
    }

    e_machine = {
        0: 'No machine',
        2: 'SPARC',
        3: 'Intel 80386',
        6: 'Intel 80486',
        7: 'Intel 80860',
        9: 'IBM System/370',
        18: 'SPARC 32+',
        19: 'Intel 80960',
        20: 'PPC',
        21: 'PPC64',
        22: 'IBM S/390',
        43: 'SPARC V9',
        50: 'Intel IA-64',
        62: 'AMD x86-64',
    }

    e_type = {
        0: 'No file type',
        1: 'Relocatable file',
        2: 'Executable file',
        3: 'Shared object file',
        4: 'Core file',
        65280: 'Processor-specific',
        65535: 'Processor-specific',
    }

    sh_type = {
        0: 'NULL',
        1: 'PROGBITS',
        2: 'SYMTAB',
        3: 'STRTAB',
        4: 'RELA',
        5: 'HASH',
        6: 'DYNAMIC',
        7: 'NOTE',
        8: 'NOBITS',
        9: 'REL',
        10: 'SHLIB',
        11: 'DYNSYM',
        12: 'NUM',
        14: 'INIT_ARRAY',
        15: 'FINI_ARRAY',
        16: 'PREINIT_ARRAY',
        17: 'GROUP',
        18: 'SYMTAB_SHNDX',
        1879048181: 'GNU_ATTR', 
        1879048182: 'GNU_HASH', 
        1879048183: 'GNU_LIBLIST', 
        1879048184: 'CHECKSUM', 
        1879048189: 'VERDEF', 
        1879048190: 'VERNEED', 
        1879048191: 'VERSYM', 
        1879048192: 'LOPROC',
        2147483647: 'HIPROC',
        2147483648: 'LOUSER',
        4294967295: 'HIUSER'
    }

    sh_flags = {
        1: 'W',
        2: 'A',
        4: 'X',
        16: 'M',
        32: 'S',
        64: 'I',
        128: 'L',
        256: 'N',
        512: 'G',
        1024: 'T',
        267386880: 'K',
        1073741824: 'O',
        2147483648: 'E',
        4026531840: 'P'
    }


    data = ''

    ## Check if data is piped
    if not sys.stdin.isatty():
        data = sys.stdin.read()

    else:
        ## Check if a file path was sent in
        if len(sys.argv) > 1:
            path = sys.argv[1]

            if os.path.exists(path):
                with open(path, mode='rb') as f:
                    data = f.read()

            else:
                print("Cannot open path '{0}'".format(path))
                sys.exit()

    endian = ">"

    ## Check magic
    magic = struct.unpack("4B", data[0:4])
    magic = "".join(["{:x}".format(x) for x in magic])

    if magic != '7f454c46':
            print("Input is not ELF file data")
            sys.exit()

    (elfclass, elfdata, elfversion, osabi) = struct.unpack("=4B", data[4:8])
    ## ignoring ABI version since it should be zero

    print("{0} {1} ({2})".format(
            ei_class[elfclass],
            ei_version[elfversion],
            ei_data[elfdata]
            ))

    if (elfdata == 1): endian = "<" 

    (etype, emachine, eversion,
        eentry, phoff, shoff,
        flags, ehsize,
        phentsize, phnum,
        shentsize, shnum, shstrndx
    ) = struct.unpack(endian+"2H5L6H", data[16:52])

    print("Type: {:s}".format(e_type.get(etype, str(etype))))
    print("OS ABI: {:s}".format(os_abi.get(osabi, str(osabi))))
    print("Machine: {:s}".format(e_machine.get(emachine, str(emachine))))
    print("Version: 0x{:02x}".format(eversion))
    print("Entry: 0x{:08x}".format(eentry))
    print("Program headers offset: {:,} bytes".format(phoff))
    print("Section headers offset: {:,} bytes".format(shoff))
    print("Flags: 0x{:08x}".format(flags))
    print("Elf header size: {:,} bytes".format(ehsize))
    print("Program header entry size: {:,} bytes".format(phentsize))
    print("Number of program headers: {:d}".format(phnum))
    print("Section header entry size: {:,} bytes".format(shentsize))
    print("Number of section headers: {:d}".format(shnum))
    print("Section header string table index: {:d}".format(shstrndx))

    if phnum > 0:
        print("\nProgram Headers:")
        print("  TBD\n")

    if shnum > 0:
        ## Section header representation
        ShHdr = namedtuple('ShHdr', 'name t flags addr offset size link info addralign entsize')

        ## Build all section headers into an array
        s_headers = []
        for x in range(0, shnum):
            start = shoff + (shentsize*x)
            end = start + shentsize
            s_headers.append(ShHdr._make(struct.unpack(endian+"10L", data[start:end])))

        ## Get section header string table to get section names
        strtab_ent = s_headers[shstrndx]
        strtab_data = data[strtab_ent.offset:strtab_ent.offset+strtab_ent.size]
        sh_flags_keys = sorted(sh_flags.keys())

        for x in range(0, shnum):
            ## Where name for the section starts within the string table
            name_idx = s_headers[x].name

            ## From name_idx, find the next nul byte to get the name length
            name_len = strtab_data[name_idx:strtab_ent.size].find('\x00')

            ## Replace property values in SH rep
            s_headers[x] = s_headers[x]._replace(
                ## Name index to string
                name = strtab_data[name_idx:name_idx+name_len], 
                ## Get type as a string
                t = sh_type.get(s_headers[x].t, s_headers[x].t),
                ## Translate flag bits to a string
                flags = ''.join([sh_flags.get(b, '?') for b in sh_flags_keys if s_headers[x].flags & b]) 
            )

        print("\nSection Headers:")
        print("{:4s} {:20s}{:15s}{:8s} {:6s} {:6s} {:2s} {:3s} {:2s} {:3s} {:2s}".format(
            "", "Name", "Type", "Addr", "Off", "Size", 
            "ES", "Flg", "Lk", "Inf", "Al"
        ))

        for x in range(0, shnum):
            sh = s_headers[x]

            print("[{:>2d}] {:20s}{:15s}{:08x} {:06x} {:06x} {:02x} {:3s} {:2d} {:3d} {:2d}".format(
                x, sh.name, sh.t, sh.addr, sh.offset, sh.size, sh.entsize, sh.flags,
                sh.link, sh.info, sh.addralign
            ))


