"""Process the `confusables.txt` file from Unicode"""
# That file should be available from: https://www.unicode.org/Public/


import unicodedata

def char_repr(char):
    if char.isascii() and 32 < ord(char) < 127:
        return char
    try:
        return f"\\N{{{unicodedata.name(char)}}}"
    except ValueError:
        if ord(char) <= 0xffff:
            return f"\\u{ord(char):04x}"
        return f"\\U{ord(char):08x}"

# Check that ASCII characters don`t decompose
assert all(unicodedata.decomposition(chr(c)) == '' for c in range(128))


filename = 'confusables.txt'
confusables = {}
with open(filename, encoding='utf-8-sig') as file:
    in_header = True
    print(f'# Generated from {filename} which had the following header:')
    for line in file:
        line, sep, comment = line.strip().partition('#')
        if in_header:
            if line.strip():
                in_header = False
            else:
                print('    #', comment)
        if not line:
            continue

        src, target, ma = line.split(';')
        src = int(src, 16)
        target = ''.join(chr(int(t, 16)) for t in target.split())
        confusables[src] = target

print()
print()
print('ascii_confusable_map = {')

for src, target in confusables.items():
    # The mapping in confusables.txt should be idempotent, but let's
    # verify that.
    for t in target:
        assert ord(t) not in confusables, char_repr(t)

    if src < 128:
        # We assume that in fonts used with programming languages,
        # ASCII-only text is not confusable with other ASCII-only text.
        # (Excluding control chars, those are handled separately.)
        print(f"# ignoring: {char_repr(chr(src))} ->",
              ''.join(char_repr(t) for t in target))
        if not target.isascii() and len(target) == 1:
            # We sssume ASCII characters map only to other ASCII characters,
            # or to multiple characters (`%` to circle-slash-circle).
            # This means skeletons that can be ASCII either:
            # - are ASCII, or
            # - are not confusable in a fixed-width font.
            raise ValueError('Simplifying assumption not true')
    else:
        if target.isascii():
            print(f"    0x{src:x}: {target!r},  # {char_repr(chr(src))}")

print('}')
