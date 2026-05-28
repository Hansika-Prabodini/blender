# SPDX-FileCopyrightText: 2009-2023 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

if 1:
    # Print once every 1000
    GEN_PATH = True
    PRINT_DATA = False
    PRINT_DATA_INT = 1000
    VERBOSE = False
    VERBOSE_TYPE = False
    MAX_RECURSIVE = 8
else:
    # Print everything
    GEN_PATH = True
    PRINT_DATA = True
    PRINT_DATA_INT = 0
    VERBOSE = False
    VERBOSE_TYPE = False
    MAX_RECURSIVE = 8

seek_count = [0]


def seek(r, txt, recurs):

    # Cache frequently used globals and builtins to locals to reduce lookup overhead.
    PRINT_DATA_INT_l = PRINT_DATA_INT
    PRINT_DATA_l = PRINT_DATA
    GEN_PATH_l = GEN_PATH
    VERBOSE_l = VERBOSE
    VERBOSE_TYPE_l = VERBOSE_TYPE
    MAX_RECURSIVE_l = MAX_RECURSIVE

    _dir = dir
    _getattr = getattr
    _len = len
    _str = str

    seek_count[0] += 1

    if PRINT_DATA_INT_l:
        if not (seek_count[0] % PRINT_DATA_INT_l):
            print(seek_count[0], txt)

    if PRINT_DATA_l:
        print(txt)

    newtxt = ''

    if recurs > MAX_RECURSIVE_l:
        # print ("Recursion is over max")
        # print (txt)
        return

    type_r = type(r)

    # print(type_r)
    # print(dir(r))

    # basic types
    if type_r in {float, int, bool, type(None)}:
        if PRINT_DATA_l:
            print(txt + ' -> ' + _str(r))
        return

    if type_r is str:
        if PRINT_DATA_l:
            print(txt + ' -> "' + _str(r) + '"')
        return

    # Try to get mapping keys once (avoid calling r.keys() multiple times).
    try:
        keys_attr = _getattr(r, "keys", None)
        if callable(keys_attr):
            try:
                keys = keys_attr()
            except Exception:
                keys = None
        else:
            keys = None
    except Exception:
        keys = None

    if keys is not None:
        if PRINT_DATA_l:
            print(txt + '.keys() - ' + _str(keys))

    try:
        __members__ = _dir(r)
    except Exception:
        __members__ = []

    for item in __members__:
        if item.startswith("__"):
            continue

        if GEN_PATH_l:
            newtxt = txt + '.' + item

        if item == 'rna_type' and VERBOSE_TYPE_l is False:  # just avoid because it spits out loads of data
            continue

        value = _getattr(r, item, None)

        seek(value, newtxt, recurs + 1)

    if keys:
        for k in keys:
            if GEN_PATH_l:
                newtxt = txt + '["' + k + '"]'
            # preserve original exception semantics by calling __getitem__ directly
            seek(r.__getitem__(k), newtxt, recurs + 1)

    else:
        try:
            length = _len(r)
        except Exception:
            length = 0

        if VERBOSE_l is False and length >= 4:
            for i in (0, length - 1):
                if i > 0:
                    if PRINT_DATA_l:
                        print((" " * _len(txt)) + " ... skipping " + _str(length - 2) + " items ...")

                if GEN_PATH_l:
                    newtxt = txt + '[' + _str(i) + ']'
                seek(r[i], newtxt, recurs + 1)
        else:
            for i in range(length):
                if GEN_PATH_l:
                    newtxt = txt + '[' + _str(i) + ']'
                seek(r[i], newtxt, recurs + 1)


seek(bpy.data, 'bpy.data', 0)
# seek(bpy.types, 'bpy.types', 0)
'''
for d in dir(bpy.types):
    t = getattr(bpy.types, d)
    try:
        r = t.bl_rna
    except AttributeError:
        r = None
    if r:
        seek(r, 'bpy.types.' + d + '.bl_rna', 0)
'''

print("iter over ", seek_count, "rna items")