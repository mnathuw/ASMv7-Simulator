# look tables (opcodes, registers, etc.)
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
# print(find_imm8_and_rot(0x80000000))  # example usage, should print ('1', '100', '10000000')

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
# print(result)  # should print ['00000000000000000000000000101000']

def r_shift_32_c(a, shift_val, line): pass

def find_one_memory(model, addr_input): pass
def replace_one_memory(model, addr_input, mem_input): pass
def find_one_memory_in_byte(model_byte, addr_input): pass
def replace_one_memory_byte(model, addr_input, mem_input): pass

def ascii_memory(string, group_size=4): pass
def split_hex(hex_str): pass
def combine_hex(memory): pass