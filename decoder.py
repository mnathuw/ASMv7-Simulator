# convert the binary string to a decimal integer
def Decoder(value):
    if value.startswith('#'):
        value = value[1:]

    is_binary = True
    for char in value:
        if char != '0' and char != '1':
            is_binary = False
            break

    if is_binary and len(value) == 32:
        return int(value, 2)
    else:
        return int(value)

# print(Decoder('00000000000000000000000000001010'))  # example usage, should print 10