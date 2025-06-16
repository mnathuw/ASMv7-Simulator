# look tables (opcodes, registers, etc.)
from PyQt6 import QtCore, QtGui, QtWidgets
from decoder import Decoder
from encoder import Encoder
import string

line_edit_dict = {
    "r0": None,
    "r1": None,
    "r2": None,
    "r3": None,
    "r4": None,
    "r5": None,
    "r6": None,
    "r7": None,
    "r8": None,
    "r9": None,
    "r10": None,
    "r11": None,
    "r12": None,
    "sp": None,
    "lr": None,
    "pc": None,
}

condition_dict = {
    "n": None,
    "z": None,
    "c": None,
    "v": None
}

# 4-bit opcode fields inside 32-bit instruction
# used in the data processing instructions
# e.g. add r0, r1, r2
data_opcode_memory_dict = {
    "and": '0000', "tst": '0000',
    "bic": '0001',
    "orr": '0010', "mov": '0010',
    "orn": '0011', "mvn": '0011',
    "eor": '0100', "teq": '0100',
    "add": '1000', "cmn": '1000',
    "adc": '1010',
    "sbc": '1011',
    "sub": '1101',  "cmp": '1101',
    "rsb": '1110',
}

# sp (r13) is the stack pointer, lr (r14) is the link register, pc (r15) is the program counter
# source: 2-1 ARM Architerture Register Set and Memory
# used in the data processing instructions
register_memory_dict = {
    "r0": '0000',
    "r1": '0001',
    "r2": '0010',
    "r3": '0011',
    "r4": '0100',
    "r5": '0101',
    "r6": '0110',
    "r7": '0111',
    "r8": '1000',
    "r9": '1001',
    "r10": '1010',
    "r11": '1011',
    "r12": '1100',
    "sp": '1101',
    "lr": '1110',
    "pc": '1111'
}

# 4-bit condition codes for the instruction
# source: 2-2 ARM Architerture Instruction Set
# used in the data processing instructions
# e.g. add r0, r1, r2, eq
condition_memory_dict = {
    "eq": '0000',
    "ne": '0001',
    "cs": '0010', "hs": '0010',
    "cc": '0010', "lo": '0011',
    "mi": '0100',
    "pl": '0101',
    "vs": '0110',
    "vc": '0111',
    "hi": '1000',
    "ls": '1001',
    "ge": '1010',
    "lt": '1011',
    "gt": '1100',
    "le": '1101',
    "al": '1110',
}

# 2-bit shift type for the instruction
# used in the shift and rotate operations
# e.g. lsl r0, r1, #2
shift_memory_dict = {
    "lsl": '00',
    "lsr": '01',
    "asr": '10',
    "ror": '11',
    "rrx": '11'
}

# ARM can only store 8-bit number (0 to 255)
# instead of storing a big number like 0x80000000, we can store 0x2 rotated right by 30 bits
def find_imm8_and_rot(value):
    # default binary outputs
    i = "0"
    imm3 = "000"
    imm8 = "00000000"
    if value == 0:
        return i, imm3, imm8
    # try to find a valid rotation and immediate value
    for rot in range(16):
        shift = rot * 2
        # convert value to a 32-bit binary string
        binary = format(value & 0xFFFFFFFF, '032b')
        # rotate right: move the last shift bits to the front
        if shift == 0:
            rotated = binary
        else:
            right_part = binary[32 - shift:]   # last bits
            left_part = binary[:32 - shift]    # first bits
            rotated = right_part + left_part   # rotated binary
        # turn the rotated binary back into a number
        rotated_value = int(rotated, 2)
        # check if it's small enough (fits in 8 bits)
        if rotated_value <= 255:
            # save it as an 8-bit binary string
            imm8_bits = format(rotated_value, '08b')
            # convert rotation number (0–15) to 4-bit binary
            rot_bin = format(rot, '04b')  # e.g., 13 = '1101'
            # split it:
            i_bit = rot_bin[0]  # first bit
            imm3_bits = rot_bin[1] + rot_bin[2] + rot_bin[3]  # last 3 bits
            return i_bit, imm3_bits, imm8_bits

    # if no valid rotation is found, return default values
    return i, imm3, imm8
# print(find_imm8_and_rot(0x80000000))  # example usage, output: ('1', '100', '10000000')

# convert 32-bit hex number like FFFFFFFE to signed integer
def twos_complement_to_signed(hex_str):
    num = int(hex_str, 16)
    if num >= 2**31:
        num -= 2**32
    return num
# print(twos_complement_to_signed('FFFFFFFE'))  # output: -2
# print(twos_complement_to_signed('00000002'))  # output: 2

# checks if the first character of a string is a digit or special character
def is_special_or_digit(word):
    if word == "":
        return False
    first = word[0]
    if first.isdigit():
        return True
    if first in string.punctuation:
        return True
    return False
# print (is_special_or_digit("123abc"))  # True (start with digit)
# print (is_special_or_digit("#fun"))  # True (start with special character)
# print (is_special_or_digit("hello"))  # False

# parse labels from assembly lines
def parse_labels(lines):
    labels = {}               # dictionary to hold label: [instructions]
    current_label = None      # tracks the current label we're under
    code_lines = []           # all actual instruction lines

    # remove empty or None lines
    cleaned_lines = []
    for line in lines:
        if line:  # make sure it's not None or empty string
            stripped = line.strip()  # remove spaces at the beginning and end
            if stripped:  # make sure it's not just spaces
                cleaned_lines.append(stripped)

    for line in cleaned_lines:
        if line.endswith(":") and not is_special_or_digit(line):
            # found a label (e.g., 'loop:')
            label_name = line[:-1]  # remove the colon
            labels[label_name] = []
            current_label = label_name
        elif current_label:
            # this line belongs to the last label we saw
            labels[current_label].append(line)
            code_lines.append(line)
        else:
            # no label, just a standalone instruction
            code_lines.append(line)

    return labels, code_lines
# lines = ["   mov r0, #1  ", "", "   ", None, "add r1, r2, #3"]
# print(parse_labels(lines))

# check if the condition is met based on the flags
def check_condition(condition):
    # get flag values
    n = condition_dict.get("n").text()
    z = condition_dict.get("z").text()
    c = condition_dict.get("c").text()
    v = condition_dict.get("v").text()

    condition = condition.lower()

    if condition == "eq":
        return z == '1'
    elif condition == "ne":
        return z == '0'
    elif condition in ("cs", "hs"):
        return c == '1'
    elif condition in ("cc", "lo"):
        return c == '0'
    elif condition == "mi":
        return n == '1'
    elif condition == "pl":
        return n == '0'
    elif condition == "vs":
        return v == '1'
    elif condition == "vc":
        return v == '0'
    elif condition == "hi":
        return c == '1' and z == '0'
    elif condition == "ls":
        return c == '0' or z == '1'
    elif condition == "ge":
        return n == v
    elif condition == "lt":
        return n != v
    elif condition == "gt":
        return z == '0' and n == v
    elif condition == "le":
        return z == '1' or n != v
    elif condition == "al" or condition == "":
        return True
    else:
        return False

# LSL (Left Shift Logical) 32-bit carry
def l_shift_32_c(a, shift_val, line):
    result = []
    is_valid_a = isinstance(a, str) and len(a) == 32
    is_valid_shift = isinstance(shift_val, int) and 0 <= shift_val <= 32
    if not (is_valid_a and is_valid_shift):
        print(f"Error: Invalid input for left shift operation in line '{line}'")
        return None, None
    carry = None

    # no shifting is needed, carry is '0'
    if shift_val == 0:
        carry = '0'
    else:
        for i in range(shift_val):
            carry = a[0]
            a = a[1:] + '0'
    result.append(a)
    return result, carry
# a = '00000000000000000000000000001010'
# shift_val = 2
# result, carry = l_shift_32_c(a, shift_val, "example line")
# print(result)  # output: ['00000000000000000000000000101000']

# LSR (Logical Shift Right) 32-bit carry
def r_shift_32_c(a, shift_val, line):
    result = []
    is_valid_a = isinstance(a, str) and len(a) == 32
    is_valid_shift = isinstance(shift_val, int) and 0 <= shift_val <= 32
    if not (is_valid_a and is_valid_shift):
        print(f"Error: Invalid input for right shift operation in line '{line}'")
        return None, None
    carry = None

    # no shifting is needed, carry is '0'
    if shift_val == 0:
        carry = '0'
    else:
        for i in range(shift_val):
            carry = a[-1]
            a = '0' + a[:-1]
    result.append(a)
    return result, carry
# a = '00000000000000000000000000001010'
# shift_val = 2
# result, carry = ror_shift_32_c(a, shift_val, "example line")
# print(result)  # output: ['10000000000000000000000000001010']

# AND logic operation for 32-bit binary strings
def and_32(str1, str2, line):
    result = []
    is_valid_input = (
        isinstance(str1, str) and len(str1) == 32 and
        isinstance(str2, str) and len(str2) == 32
    )

    if not is_valid_input:
        print(f"Error: Invalid input for AND logic operation in line '{line}'")
        return None

    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 & num2
    result_str = f"{result_int:032b}"

    # optional decoding/encoding step
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)

    result.append(result_str)
    return result
# str1 = '11110000111100001111000011110000'
# str2 = '10101010101010101010101010101010'
# result = and_32(str1, str2, "example line")
# print(result) # output: ['10100000101000001010000010100000']

# OR logic operation for 32-bit binary strings
def or_32(str1, str2, line):
    result = []
    is_valid_input = (
        isinstance(str1, str) and len(str1) == 32 and
        isinstance(str2, str) and len(str2) == 32
    )

    if not is_valid_input:
        print(f"Error: Invalid input for OR logic operation in line '{line}'")
        return None

    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 | num2
    result_str = f"{result_int:032b}"

    # optional: Decoder and Encoder processing
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)

    result.append(result_str)
    return result
# str1 = '11110000111100001111000011110000'
# str2 = '10101010101010101010101010101010'
# result = or_32(str1, str2, "example line")
# print(result)  # output: ['11111010111110101111101011111010']

# XOR logic operation for 32-bit binary strings
def xor_32(str1, str2, line):
    result = []
    is_valid_input = (
        isinstance(str1, str) and len(str1) == 32 and
        isinstance(str2, str) and len(str2) == 32
    )

    if not is_valid_input:
        print(f"Error: Invalid input for XOR logic operation in line '{line}'")
        return None

    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 ^ num2
    result_str = f"{result_int:032b}"

    # Optional: Decoder and Encoder processing
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)

    result.append(result_str)
    return result
# str1 = '11110000111100001111000011110000'
# str2 = '10101010101010101010101010101010'
# result = xor_32(str1, str2, "example line")
# print(result)  # output: ['01011010010110101101101001011010']
# subtraction operation for 32-bit binary strings
def sub_32(temporary, line):
    result = []
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 - num2
    carry = '1' if result_int >= 0 else '0'
    result_str = f"{result_int:032b}"
    overflow = detect_overflow_sub(str1, str2, result_str)
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)
    result.append(result_str)
    return result, carry, overflow

# detect overflow in subtraction operation
def detect_overflow_sub(a, b, res):
    a_sign = a[0]
    b_sign = b[0]
    res_sign = res[0]
    if a_sign != b_sign and a_sign != res_sign:
        return '1'
    return '0'
# print(sub_32(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: (['00000000000000000000000000000101'], '1', '0')

# add operation for 32-bit binary strings
def add_32(temporary, line):
    result = []
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 + num2
    carry = '1' if (result_int >> 32) & 1 else '0'
    result_str = f"{result_int & ((1 << 32) - 1):032b}"
    overflow = detect_overflow_add(str1, str2, result_str)
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)
    result.append(result_str)
    return result, carry, overflow

# detect overflow in addition operation
def detect_overflow_add(a, b, res):
    a_sign = a[0]
    b_sign = b[0]
    res_sign = res[0]
    if a_sign == b_sign and a_sign != res_sign:
        return '1'
    return '0'
# print(add_32(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: (['00000000000000000000000000001111'], '0', '0')

# multiplication operation for 32-bit binary strings
def mul_32(temporary, line):
    result = []
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 * num2
    result_str = f"{result_int & ((1 << 32) - 1):032b}"
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)
    result.append(result_str)
    return result
# print(mul_32(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000101010']

# multiplication operation for 64-bit binary strings (signed)
def mul_64_unsigned(temporary, line):
    result = []
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 * num2
    lower_32 = result_int & ((1 << 32) - 1)
    upper_32 = (result_int >> 32) & ((1 << 32) - 1)
    lower_32_str = f"{lower_32:032b}"
    upper_32_str = f"{upper_32:032b}"
    result.append(lower_32_str)
    result.append(upper_32_str)
    return result
# print(mul_64_unsigned(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000110010', '00000000000000000000000000000000']

# multiplication operation for 64-bit binary strings (signed)
def mul_64_signed(temporary, line):
    result = []
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    if num1 >= 2**31:
        num1 -= 2**32
    num2 = int(str2, 2)
    if num2 >= 2**31:
        num2 -= 2**32
    result_int = num1 * num2
    lower_32 = result_int & ((1 << 32) - 1)
    upper_32 = (result_int >> 32) & ((1 << 32) - 1)
    if lower_32 >= 2**31:
        lower_32 -= 2**32
    if upper_32 >= 2**31:
        upper_32 -= 2**32
    lower_32_str = f"{lower_32 & ((1 << 32) - 1):032b}"
    upper_32_str = f"{upper_32 & ((1 << 32) - 1):032b}"
    result.append(lower_32_str)
    result.append(upper_32_str)
    return result
# print(mul_64_signed(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000110010', '00000000000000000000000000000000']

# division operation for 32-bit binary strings (unsigned)
def divide_32_unsigned(temporary, line):
    print(temporary)
    result = []
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    num2 = int(str2, 2)
    if num2 == 0:
        result_str = Encoder(0)
        result.append(result_str)
        return result
    result_int = num1 // num2
    result_str = f"{result_int:032b}"
    result.append(result_str)
    return result
# print(divide_32_unsigned(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000001010', '00000000000000000000000000000101'] ['00000000000000000000000000000100']

# division operation for 32-bit binary strings (signed)
def divide_32_signed(temporary, line):
    result = []
    print(temporary)
    if len(temporary) != 2:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        QtWidgets.QMessageBox.critical(None, "Error", "Undefined input for an arithmetic operation - " + line)
        return None
    num1 = int(str1, 2)
    if num1 >= 2**31:
        num1 -= 2**32
    num2 = int(str2, 2)
    if num2 >= 2**31:
        num2 -= 2**32
    if num2 == 0:
        result_str = Encoder(0)
        result.append(result_str)
        return result
    result_int = num1 // num2
    if result_int < 0:
        result_int += 2**32
    result_str = f"{result_int & ((1 << 32) - 1):032b}"
    result.append(result_str)
    return result
# print(divide_32_signed(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000000100']

# complement operation for binary strings
def complement(binary_str):
    if not isinstance(binary_str, str) or not all(bit in '01' for bit in binary_str):
        raise ValueError("Undefined input for a complement")
    complement_str = ''.join('1' if bit == '0' else '0' for bit in binary_str)
    return complement_str
# print(complement("101010"))  # output: 010101

# find positions of '1' bits in a binary string
def find_bit_positions(binary_str):
    return [i for i, bit in enumerate(binary_str) if bit == '1']
# print(find_bit_positions("1011001"))  # output: [0, 2, 3, 6]

# determine the rotation needed for a single bit in a binary string
def determine_rotation_for_single_bit(position):
    return ((31 - position[0]) // 2) * 2
# print(determine_rotation_for_single_bit([29]))  # output: 2

# determine the rotation needed for multiple bits in a binary string
def determine_rotation_for_multiple_bits(positions):
    first_position = positions[0]
    last_position = positions[-1]
    if last_position - first_position > 8:
        return None
    return  ((31 - last_position) // 2) * 2
# print(determine_rotation_for_multiple_bits([5, 16]))  # output: None
# print(determine_rotation_for_multiple_bits([5, 6, 7, 8]))  # output: 22

# convert a number to a 32-bit binary string
def process_binary(num):
    if num < 0:
        num = abs(num) - 1
    binary_str = Encoder(num)
    if len(binary_str) != 32:
        return None
    positions = find_bit_positions(binary_str)
    num_ones = len(positions)
    if int(binary_str, 2) > 255 and (31 in positions or 30 in positions):
        return None
    if num_ones == 0:
        rotation = 0
    elif num_ones == 1:
        rotation = determine_rotation_for_single_bit(positions)
    elif num_ones > 1:
        rotation = determine_rotation_for_multiple_bits(positions)
    if rotation == None:
        return None
    rotated_str = binary_str[-rotation:] + binary_str[:-rotation]
    last_8_bits = rotated_str[-8:]
    rotation_bits = format(15 - (rotation // 2), '04b')
    if int(binary_str, 2) < 256:
        result = "0000" + binary_str[-8:]
        return result
    result = rotation_bits + last_8_bits
    return result
# print(process_binary(0x80000000))  # output: '000000000010'

# convert a string to a list of hex ASCII codes, grouped and reversed
def ascii_memory(string, group_size=4):
    hex_codes = [format(ord(c), 'x') for c in string]
    while len(hex_codes) % group_size != 0:
        hex_codes.append('00')
    ascii_memory = [''.join(hex_codes[i:i + group_size][::-1]) for i in range(0, len(hex_codes), group_size)]
    return ascii_memory
# print(ascii_memory("Hello, World!"))  # output: ['6c6c6548', '57202c6f', '646c726f', '00000021']

def split_hex(hex_str):
    bytes_list = [f"{hex_str[i:i+2]}" for i in range(0, len(hex_str), 2)]
    bytes_list.reverse()
    memory = " ".join(bytes_list)
    return memory
# print(split_hex("1234567890abcdef"))  # output: 'ef cd ab 90 78 56 34 12'

# combine a list of hex bytes into a single hex string
def combine_hex(memory):
    bytes_list = memory.split()
    bytes_list.reverse()
    hex_str = "".join(byte for byte in bytes_list)
    return hex_str
# print(combine_hex("ef cd ab 90 78 56 34 12"))  # output: '1234567890abcdef'

# replace memory addresses in a model data structure
def replace_memory(model, listAddr, listMem):
    replacement_dict = dict(zip(listAddr, listMem))
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        for address in listAddr:
            text = QtGui.QStandardItem(replacement_dict[address])
            text.setFlags(text.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            if int(address, 16) == int(addr, 16):
                model.setItem(row, 1, text)
            if addr_next and int(address, 16) > int(addr, 16) and int(address, 16) < int(addr_next, 16):
                num = int((int(address, 16) - int(addr, 16)) / 4) + 1
                model.setItem(row, num, text)
            if not addr_next and int(address, 16) > int(addr, 16):
                num = int((int(address, 16) - int(addr, 16)) / 4) + 1
                model.setItem(row, num, text)


# replace_memory_byte function to update memory model data
def replace_memory_byte(model_byte, listAddr, listMem):
    for i in range(len(listMem)):
        listMem[i] = split_hex(listMem[i])
    replacement_dict = dict(zip(listAddr, listMem))
    max_row = model_byte.rowCount() - 1
    for row in range(1, model_byte.rowCount()):
        item_addr = model_byte.item(row, 0)
        if row != max_row:
            item_addr_next = model_byte.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        for address in listAddr:
            text = QtGui.QStandardItem(replacement_dict[address])
            if int(address, 16) == int(addr, 16):
                model_byte.setItem(row, 1, text)
            if addr_next and int(address, 16) > int(addr, 16) and int(address, 16) < int(addr_next, 16):
                num = int((int(address, 16) - int(addr, 16)) / 4) + 1
                model_byte.setItem(row, num, text)
            if not addr_next and int(address, 16) > int(addr, 16):
                num = int((int(address, 16) - int(addr, 16)) / 4) + 1
                model_byte.setItem(row, num, text)
    for i in range(len(listMem)):
        listMem[i] = combine_hex(listMem[i])

# find_one_memory function to search for a specific memory address
def find_one_memory(model, addr_input):
    mem = "00"
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            mem = model.item(row, 1).text()
            found = True
            return mem
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return mem

# find_one_memory_in_byte function to search for a specific byte at an address
def find_one_memory_in_byte(model_byte, addr_input):
    mem_out = "00"
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    for row in range(1, model_byte.rowCount()):
        item_addr = model_byte.item(row, 0)
        if item_addr:
            addr = item_addr.text()
        if search_value - twos_complement_to_signed(addr) == 0:
            mem = model_byte.item(row, 1).text()
            mems = mem.split()
            mem_out = mems[0]
            found = True
            return mem_out
        elif search_value - twos_complement_to_signed(addr) == 1:
            mem = model_byte.item(row, 1).text()
            mems = mem.split()
            mem_out = mems[1]
            found = True
            return mem_out
        elif search_value - twos_complement_to_signed(addr) == 2:
            mem = model_byte.item(row, 1).text()
            mems = mem.split()
            mem_out = mems[2]
            found = True
            return mem_out
        elif search_value - twos_complement_to_signed(addr) == 3:
            mem = model_byte.item(row, 1).text()
            mems = mem.split()
            mem_out = mems[3]
            found = True
            return mem_out
    if not found:
        last_item_value = twos_complement_to_signed(model_byte.item(model_byte.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return mem_out

# find_one_memory_in_halfword function to search for a halfword at an address
def find_one_memory_in_halfword(model_byte, addr_input):
    mem_out = "0000"
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    for row in range(1, model_byte.rowCount()):
        item_addr = model_byte.item(row, 0)
        if item_addr:
            addr = item_addr.text()
        if search_value - twos_complement_to_signed(addr) == 0:
            mem = model_byte.item(row, 1).text()
            mems = mem.split()
            mem_out = mems[1] + mems[0]
            found = True
            return mem_out
        elif search_value - twos_complement_to_signed(addr) == 1:
            found = True
            return mem_out
        elif search_value - twos_complement_to_signed(addr) == 2:
            mem = model_byte.item(row, 1).text()
            mems = mem.split()
            mem_out = mems[3] + mems[2]
            found = True
            return mem_out
        elif search_value - twos_complement_to_signed(addr) == 3:
            found = True
            return mem_out
    if not found:
        last_item_value = twos_complement_to_signed(model_byte.item(model_byte.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return mem_out

# replace_one_memory function to update a specific memory address
def replace_one_memory(model, addr_input, mem_input):
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model.item(row, 1).setText(mem_input)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int(((search_value - twos_complement_to_signed(addr)) / 4) + 1)
            model.item(row, num).setText(mem_input)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int(((search_value - twos_complement_to_signed(addr, 16)) / 4) + 1)
            model.item(row, num).setText(mem_input)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return

# replace_one_memory_in_byte function to update a specific byte at an address
def replace_one_memory_byte(model, addr_input, mem_input):
    mem_input = split_hex(mem_input)
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model.item(row, 1).setText(mem_input)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model.item(row, num).setText(mem_input)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model.item(row, num).setText(mem_input)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return

    mem_input = split_hex(mem_input)
    mem_input = mem_input.split()
    mem_input_byte = mem_input[0]
    num_addr = int(addr_input, 16)
    surplus = num_addr % 4
    num_addr = num_addr - surplus
    addr_input = format(num_addr, "08x")
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, 1).setText(model_text)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, num).setText(model_text)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, num).setText(model_text)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return

# replace_one_memory_in_byte function to update a specific byte at an address
def replace_one_memory_in_byte(model, addr_input, mem_input):
    mem_input = split_hex(mem_input)
    mem_input = mem_input.split()
    mem_input_byte = mem_input[0]
    num_addr = int(addr_input, 16)
    surplus = num_addr % 4
    num_addr = num_addr - surplus
    addr_input = format(num_addr, "08x")
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, 1).setText(model_text)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, num).setText(model_text)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, num).setText(model_text)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],
#     ["0x1000", "EF", "BE", "AD", "DE"],
#     ["0x1010", "CE", "FA", "ED", "FE"]
# ]
# replace_one_memory_byte(model_data, "0x1000", "AABBCCDD")  # updates Col1 of row 1
# replace_one_memory_byte(model_data, "0x1002", "11")        # updates Col3 of row 1
# replace_one_memory_byte(model_data, "0x1014", "22")        # updates Col2 of row 2
# print(model_data)

def replace_one_memory_byte_in_byte(model, addr_input, mem_input):
    mem_input = split_hex(mem_input)
    mem_input = mem_input.split()
    mem_input_byte = mem_input[0]
    num_addr = int(addr_input, 16)
    surplus = num_addr % 4
    num_addr = num_addr - surplus
    addr_input = format(num_addr, "08x")
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model_text = model.item(row, 1).text()
            model_text_byte = model_text.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model_text = split_hex(model_text)
            model.item(row, 1).setText(model_text)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = model_text.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model_text = split_hex(model_text)
            model.item(row, num).setText(model_text)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = model_text.split()
            model_text_byte[surplus] = mem_input_byte
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model_text = split_hex(model_text)
            model.item(row, num).setText(model_text)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return

# replace_one_memory_in_halfword function to update a specific halfword at an address
def replace_one_memory_in_halfword(model, addr_input, mem_input):
    mem_input = split_hex(mem_input)
    mem_input = mem_input.split()
    num_addr = int(addr_input, 16)
    surplus = num_addr % 4
    num_addr = num_addr - surplus
    addr_input = format(num_addr, "08x")
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            if surplus == 0 or surplus == 2:
                model_text_byte[0] = mem_input[0]
                model_text_byte[1] = mem_input[1]
            else:
                model_text_byte[0] = "00"
                model_text_byte[1] = "00"
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, 1).setText(model_text)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            if surplus == 0 or surplus == 2:
                model_text_byte[0] = mem_input[0]
                model_text_byte[1] = mem_input[1]
            else:
                model_text_byte[0] = "00"
                model_text_byte[1] = "00"
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, num).setText(model_text)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = split_hex(model_text)
            model_text_byte = model_text_byte.split()
            if surplus == 0 or surplus == 2:
                model_text_byte[0] = mem_input[0]
                model_text_byte[1] = mem_input[1]
            else:
                model_text_byte[0] = "00"
                model_text_byte[1] = "00"
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model.item(row, num).setText(model_text)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return

# replace_one_memory_halfword_in_byte function to update a specific halfword at an address
def replace_one_memory_halfword_in_byte(model, addr_input, mem_input):
    mem_input = split_hex(mem_input)
    mem_input = mem_input.split()
    num_addr = int(addr_input, 16)
    surplus = num_addr % 4
    num_addr = num_addr - surplus
    addr_input = format(num_addr, "08x")
    found = False
    search_value  = twos_complement_to_signed(addr_input)
    max_row = model.rowCount() - 1
    for row in range(1, model.rowCount()):
        item_addr = model.item(row, 0)
        if row != max_row:
            item_addr_next = model.item(row + 1, 0)
            addr_next = item_addr_next.text()
        if item_addr:
            addr = item_addr.text()
        if search_value == twos_complement_to_signed(addr):
            model_text = model.item(row, 1).text()
            model_text_byte = model_text.split()
            if surplus == 0 or surplus == 2:
                model_text_byte[0] = mem_input[0]
                model_text_byte[1] = mem_input[1]
            else:
                model_text_byte[0] = "00"
                model_text_byte[1] = "00"
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model_text = split_hex(model_text)
            model.item(row, 1).setText(model_text)
            found = True
            return
        if addr_next and search_value > twos_complement_to_signed(addr) and search_value < twos_complement_to_signed(addr_next):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = model_text.split()
            if surplus == 0 or surplus == 2:
                model_text_byte[0] = mem_input[0]
                model_text_byte[1] = mem_input[1]
            else:
                model_text_byte[0] = "00"
                model_text_byte[1] = "00"
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model_text = split_hex(model_text)
            model.item(row, num).setText(model_text)
            found = True
            return
        if not addr_next and search_value > twos_complement_to_signed(addr):
            num = int((search_value - twos_complement_to_signed(addr)) / 4) + 1
            model_text = model.item(row, 1).text()
            model_text_byte = model_text.split()
            if surplus == 0 or surplus == 2:
                model_text_byte[0] = mem_input[0]
                model_text_byte[1] = mem_input[1]
            else:
                model_text_byte[0] = "00"
                model_text_byte[1] = "00"
            model_text_byte.reverse()
            model_text_byte = "".join(byte for byte in model_text_byte)
            model_text = combine_hex(model_text_byte)
            model_text = split_hex(model_text)
            model.item(row, num).setText(model_text)
            found = True
            return
    if not found:
        last_item_value = twos_complement_to_signed(model.item(model.rowCount() - 1, 0).text())
        if search_value < last_item_value:
            return

