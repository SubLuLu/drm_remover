#!/usr/bin/python
# -*- coding: UTF-8 -*-

import getopt, os, sys
from constants import BOOK_FORMAT, ENCODING, HEADER_SIZE, HEADER_START
from mobi import MobiBook

"""
从命令行获取参数
-f <file> or --file=<file>
-s <serial> or --serial=<serial>
"""
def read_args(argv):
    file, serial, out = "", "", ""
    try:
        opts, _ = getopt.getopt(argv, "hf:s:o:", ["file=", "serial=", "out="])
    except getopt.GetoptError:
        print("bad option!!!")
        print("use -h to print options")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("Usage:")
            print("-f the file to decrypt")
            print("-s serial number of your kindle device")
            sys.exit()
        elif opt in ("-f", "--file"):
            file = arg
        elif opt in ("-s", "--serial"):
            serial = arg
        elif opt in ("-o", "--out"):
            out = arg
    return file, serial, out

"""
检查参数合法性
file kindle文件路径
serial kindle设备序列号(16位)
out 输出文件路径
"""
def check_args(file, serial, out):
    if file == "":
        print("Pls. input the file name")
        return False
    if serial == "":
        print("Pls. input the kindle serial number")
        return False
    if len(serial) != 16:
        print("Illegal serial number")
        return False
    if not os.path.isfile(file):
        print("No such file: " + file)
        return False
    if out != "":
        if not os.path.isdir(out):
            print(out + " is not dir")
            return False
        if not os.path.exists(out):
            print("No such dir:" + out)
            return False
    return True

"""
去除drm
以-nodrm.mobi为文件名后缀重新生成文件
"""
def remove_drm(argv):
    # 获取文件路径和设备序列号
    file, serial, out = read_args(argv)

    # 校验参数是否合法
    success = check_args(file, serial, out)
    if not success:
        sys.exit()

    print("Processing book file: " + file)
    
    # 以二进制只读方式打开文件
    rf = open(file, mode='rb')
    # 读取文件头信息
    header = rf.read(HEADER_SIZE)
    # 关闭文件
    rf.close

    format = header[HEADER_START:].decode(ENCODING)
    # 判断是否为mobi格式文件
    if not format in BOOK_FORMAT:
        print("Illegal file format")
        sys.exit()

    mb = MobiBook(file, format)

    # 获取文件名称
    title = mb.get_book_title()
    print("Book's title: %s" % title)

    # 去除DRM
    if not mb.process_book(serial):
        sys.exit()

    # 求文件后缀名
    _, temp = os.path.split(file)
    suffix = temp.split(".")[1]

    new_path = title + "-nodrm." + suffix
    if out != "":
        new_path = os.path.join(out, new_path)

    # 写入新文件
    wf = open(new_path, mode='wb+')
    wf.write(mb.get_result())
    print("Congratulations! DRM success!")
    print("New file is %s" % new_path)

def main(argv):
    remove_drm(argv)

if __name__ == "__main__":
   main(sys.argv[1:])