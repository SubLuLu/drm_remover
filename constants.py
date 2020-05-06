#!/usr/bin/python
# -*- coding: UTF-8 -*-

# mobi文件的头信息中指定的格式
BOOK_FORMAT = ("BOOKMOBI", "TEXtREAd")
BOOK_MOBI = "BOOKMOBI"
TEXTREAD = "TEXtREAd"

# 文件头信息大小
HEADER_SIZE = 68
HEADER_START = 60

# 解决不可见字符编码
ENCODING = "latin-1"
# 解决中文字符编码(书名)
UTF8 = "utf-8"

# 进度条长度
BAR_LENGTH = 32

# pid char map
CHAR_MAP3 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"