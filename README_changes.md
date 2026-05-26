# Bug Fix: `BLI_string_split_prefix` drops last character when no separator is found

## Summary

Fixed an off-by-one bug in `BLI_string_split_prefix` where the last character of the
input string was silently dropped when the string contained no separator character.

## Files Changed

### `source/blender/blenlib/intern/string_utils.cc`

**Bug:** In `BLI_string_split_prefix`, the fallthrough case (no separator found) called:

```c
BLI_strncpy(r_body, string, len);
```

`BLI_strncpy(dst, src, n)` copies at most `n - 1` characters into `dst`. Passing
`len` (the string length) as the size limit therefore only copied `len - 1` characters,
silently truncating the last character of the string.

**Fix:** Changed the call to pass `len + 1` so the full string is copied:

```c
BLI_strncpy(r_body, string, len + 1);
```

This is consistent with the equivalent fallthrough in `BLI_string_split_suffix`, which
correctly uses `memcpy(r_body, string, len + 1)`.

**Example of the incorrect behaviour before the fix:**

```c
char r_pre[64], r_body[64];
BLI_string_split_prefix("hello", 6, r_pre, r_body);
// r_pre  == ""      (correct)
// r_body == "hell"  (WRONG — last character 'o' was lost)
```

### `source/blender/blenlib/tests/BLI_string_utils_test.cc`

Added a new unit test `BLI_string_utils.BLI_string_split_prefix` covering:

- A multi-character string with no separator — verifies the full string ends up in
  `r_body` and `r_pre` is empty. This case **failed** before the fix.
- A string containing a separator (`"a.b.c"`) — verifies correct splitting into prefix
  and body.
- A single-character string with no separator — verifies the single character is
  preserved in `r_body`. This case **failed** before the fix.
