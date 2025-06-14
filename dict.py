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

# ASR (Arithmetic Shift Right) 32-bit carry
def asr_shift_32(a, shift_val, line):
    result = []
    is_valid_a = isinstance(a, str) and len(a) == 32
    is_valid_shift = isinstance(shift_val, int) and 0 <= shift_val <= 32
    if not (is_valid_a and is_valid_shift):
        print(f"Error: Invalid input for arithmetic right shift operation '{line}'")
        return None, None
    sign_bit = a[0]
    carry = '0' if shift_val == 0 else a[-shift_val]

    shifted = a
    for _ in range(shift_val):
        shifted = sign_bit + shifted[:-1]  # ASR shift
    return shifted, carry
# a = "10000000000000000000000000000001"  # 32-bit binary
# shift_val = 3
# result, carry = asr_shift_32(a, shift_val)
# print(result) # output: '11110000000000000000000000000000'

# ROR (Rotate Right) 32-bit carry
def ror_shift_32_c(a, shift_val, line):
    result = []
    is_valid_a = isinstance(a, str) and len(a) == 32
    is_valid_shift = isinstance(shift_val, int) and 0 <= shift_val <= 32
    if not (is_valid_a and is_valid_shift):
        print(f"Error: Invalid input for rotate right operation in line '{line}'")
        return None, None

    carry = None

    if shift_val == 0:
        carry = '0'
    else:
        for i in range(shift_val):
            carry = a[-1]
            a = carry + a[:-1]

    result.append(a)
    return result, carry

# a = '00000000000000000000000000001010'
# shift_val = 2
# result, carry = ror_shift_32_c(a, shift_val, "example line")
# print(result)  # output: ['10000000000000000000000000001010']

# RRX (Rotate Right with Extend) 32-bit carry
def rrx_shift_32_c(a, carry_in, line):
    result = []
    is_valid_a = isinstance(a, str) and len(a) == 32
    is_valid_carry = isinstance(carry_in, str) and len(carry_in) == 1

    if not (is_valid_a and is_valid_carry):
        print(f"Error: Invalid input for rotate right with extend operation in line '{line}'")
        return None, None

    carry_out = a[-1]
    shifted_str = carry_in + a[:-1]

    if len(shifted_str) != 32:
        print(f"Error: Shifted result is not 32 bits in line '{line}'")
        return None, None

    result.append(shifted_str)
    return result, carry_out
# a = '00000000000000000000000000001010'
# carry_in = '1'
# result, carry_out = rrx_shift_32_c(a, carry_in, "example line")
# print(result)  # output: ['10000000000000000000000000000101']

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
    # validate that 'temporary' contains exactly two 32-bit strings.
    if len(temporary) != 2:
        print(f"Error: Invalid input for an arithmetic operation in line '{line}'")
        return None

    str1, str2 = temporary[0], temporary[1]
    is_valid_input = (
        isinstance(str1, str) and len(str1) == 32 and
        isinstance(str2, str) and len(str2) == 32
    )
    if not is_valid_input:
        print(f"Error: Invalid input for an arithmetic operation in line '{line}'")
        return None

    # convert binary strings to integers and subtract.
    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 - num2

    # determine the carry. Here, we use '1' if the result is non-negative and '0' otherwise.
    carry = '1' if result_int >= 0 else '0'

    # format the result as a 32-bit binary string.
    result_str = f"{result_int:032b}"

    # detect any overflow with a custom overflow detection function.
    overflow = detect_overflow_sub(str1, str2, result_str)

    # process the result through Decoder and Encoder (assumed to be defined elsewhere).
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
        print(f"Error: Undefined input for arithmetic operation in line '{line}'")
        return None

    str1, str2 = temporary

    if not (isinstance(str1, str) and len(str1) == 32 and
            isinstance(str2, str) and len(str2) == 32):
        print(f"Error: Invalid input for arithmetic operation in line '{line}'")
        return None

    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 + num2
    # carry out is the 33rd bit (bit index 32) in the sum, if it exists
    carry = '1' if (result_int >> 32) & 1 else '0'
    # keep only the lower 32 bits
    result_str = f"{result_int & 0xFFFFFFFF:032b}"

    # detect overflow for addition
    overflow = detect_overflow_add(str1, str2, result_str)

    result_str = Decoder(result_str)
    result_str = Encoder(result_str)

    result.append(result_str)
    return result, carry, overflow

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
        print(f"Error: Undefined input for arithmetic operation in line '{line}'")
        return None

    str1, str2 = temporary

    if not (isinstance(str1, str) and len(str1) == 32 and
            isinstance(str2, str) and len(str2) == 32):
        print(f"Error: Invalid input for arithmetic operation in line '{line}'")
        return None

    num1 = int(str1, 2)
    num2 = int(str2, 2)
    # multiply the two numbers (unsigned multiplication)
    result_int = num1 * num2
    # keep only the lower 32 bits of the result (simulate 32-bit overflow)
    result_str = f"{result_int & 0xFFFFFFFF:032b}"

    # optional: apply Decoder and Encoder if needed in your system
    result_str = Decoder(result_str)
    result_str = Encoder(result_str)

    result.append(result_str)
    return result
# print(mul_32(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000101010']

def mul_64_unsigned(temporary, line):
    result = []
    if len(temporary) != 2:
        print(f"Error: Undefined input for an arithmetic operation '{line}'")
        return None
    str1, str2 = temporary
    if not (isinstance(str1, str) and len(str1) == 32 and isinstance(str2, str) and len(str2) == 32):
        print(f"Error: Invalid input for an arithmetic operation '{line}'")
        return None

    num1 = int(str1, 2)
    num2 = int(str2, 2)
    result_int = num1 * num2

    lower_32 = result_int & 0xFFFFFFFF
    upper_32 = (result_int >> 32) & 0xFFFFFFFF

    lower_32_str = f"{lower_32:032b}"
    upper_32_str = f"{upper_32:032b}"

    result.append(lower_32_str)
    result.append(upper_32_str)
    return result

# multiplication operation for 64-bit binary strings (signed)
def mul_64_signed(temporary, line):
    result = []
    if len(temporary) != 2:
        print(f"Error: Undefined input for an arithmetic operation '{line}'")
        return None
    str1, str2 = temporary
    if not (isinstance(str1, str) and len(str1) == 32 and isinstance(str2, str) and len(str2) == 32):
        print(f"Error: Invalid input for an arithmetic operation '{line}'")
        return None

    def to_signed(val):
        if val >= 2**31:
            val -= 2**32
        return val

    num1 = to_signed(int(str1, 2))
    num2 = to_signed(int(str2, 2))
    result_int = num1 * num2

    lower_32 = result_int & 0xFFFFFFFF
    upper_32 = (result_int >> 32) & 0xFFFFFFFF

    # mask again to ensure 32-bit binary strings for both parts
    lower_32_str = f"{lower_32:032b}"
    upper_32_str = f"{upper_32:032b}"

    result.append(lower_32_str)
    result.append(upper_32_str)
    return result
# print(mul_64_signed(['00000000000000000000000000001010', '00000000000000000000000000000101'], "example line"))  # output: ['00000000000000000000000000110010', '00000000000000000000000000000000']

# division operation for 32-bit binary strings (unsigned)
def divide_32_unsigned(temporary, line):
    print(temporary)
    result = []
    if len(temporary) != 2:
        print(f"Error: Undefined input for an arithmetic operation '{line}'")
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        print(f"Error: Undefined input for an arithmetic operation '{line}'")
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
        print(f"Error: Undefined input for an arithmetic operation '{line}'")
        return None
    str1 = temporary[0]
    str2 = temporary[1]
    if not isinstance(str1, str) or not isinstance(str2, str) or len(str1) != 32 or len(str2) != 32:
        print(f"Error: Undefined input for an arithmetic operation '{line}'")
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
    # create an empty string to store the result
    result = ""
    # look at each bit in the input string
    for bit in binary_str:
        # if the bit is '0', add '1' to result; if '1', add '0'
        if bit == '0':
            result += '1'
        else:
            result += '0'
    return result
# print(complement("101010"))  # output: 010101

# find positions of '1' bits in a binary string
def find_bit_positions(binary_str):
    positions = []
    # go through each bit and its index
    for i, bit in enumerate(binary_str):
        # if the bit is '1', add its index to the list
        if bit == '1':
            positions.append(i)
    return positions
# print(find_bit_positions("1011001"))  # output: [0, 2, 3, 6]

# determine the rotation needed for a single bit in a binary string
def determine_rotation_for_single_bit(position):
    # calculate rotation needed for the bit at position[0]
    distance = 31 - position[0]
    half = distance // 2
    rotation = half * 2
    return rotation
# print(determine_rotation_for_single_bit([29]))  # output: 2

# determine the rotation needed for multiple bits in a binary string
def determine_rotation_for_multiple_bits(positions):
    first_position = positions[0]
    last_position = positions[-1]
    if last_position - first_position > 8:
        return None  # range too wide, no rotation
    return ((31 - last_position) // 2) * 2
# print(determine_rotation_for_multiple_bits([5, 16]))  # output: None
# print(determine_rotation_for_multiple_bits([5, 6, 7, 8]))  # output: 22

def process_binary(num):
    # if negative, transform number
    if num < 0:
        num = abs(num) - 1
    # encode number to 32-bit binary string
    binary_str = Encoder(num)

    # validate length
    if len(binary_str) != 32:
        return None

    # find positions of bits set to '1'
    positions = find_bit_positions(binary_str)
    num_ones = len(positions)

    # if number is large and highest bits set, reject
    if int(binary_str, 2) > 255 and (31 in positions or 30 in positions):
        return None

    # determine rotation based on number of '1's
    if num_ones == 0:
        rotation = 0
    elif num_ones == 1:
        rotation = determine_rotation_for_single_bit(positions)
    elif num_ones > 1:
        rotation = determine_rotation_for_multiple_bits(positions)
    else:
        return None

    # if invalid rotation, return None
    if rotation is None:
        return None

    # rotate right by 'rotation' bits
    rotated_str = binary_str[-rotation:] + binary_str[:-rotation]

    # extract last 8 bits after rotation
    last_8_bits = rotated_str[-8:]

    # calculate 4-bit rotation encoding
    rotation_bits = format(15 - (rotation // 2), '04b')

    # if number fits in 8 bits, simplified output
    if int(binary_str, 2) < 256:
        result = "0000" + binary_str[-8:]
        return result

    # combine rotation info and last 8 bits
    result = rotation_bits + last_8_bits
    return result
# print(process_binary(0x80000000))  # output: '000000000010'

# convert a string to a list of hex ASCII codes, grouped and reversed
def ascii_memory(string, group_size=4):
    # convert each character to hex ASCII code (2 digits)
    hex_codes = []
    for char in string:
        ascii_value = ord(char)  # get ASCII number of char
        hex_code = format(ascii_value, '02x')  # convert to 2-digit hex string
        hex_codes.append(hex_code)

    # add '00' to fill the last group if needed
    while len(hex_codes) % group_size != 0:
        hex_codes.append('00')

    # group hex codes and reverse each group
    ascii_memory = []
    for i in range(0, len(hex_codes), group_size):
        group = hex_codes[i:i + group_size]
        group.reverse()
        joined_group = ''.join(group)
        ascii_memory.append(joined_group)

    # return the list of reversed groups as hex strings
    return ascii_memory
# print(ascii_memory("Hello, World!"))  # output: ['6c6c6548', '57202c6f', '646c726f', '00000021']

def split_hex(hex_str):
    bytes_list = []

    # go through the string 2 characters at a time
    for i in range(0, len(hex_str), 2):
        byte = hex_str[i:i+2]  # Get 2 characters (1 byte)
        bytes_list.append(byte)

    # reverse the order of the bytes
    bytes_list.reverse()
    # join them into a string with spaces between each byte
    memory = " ".join(bytes_list)
    return memory
# print(split_hex("1234567890abcdef"))  # output: 'ef cd ab 90 78 56 34 12'

# combine a list of hex bytes into a single hex string
def combine_hex(memory):
    # split the string by spaces to get a list of individual bytes
    bytes_list = memory.split()
    # reverse the list to go from little-endian back to big-endian
    bytes_list.reverse()
    # join all the bytes together into a single string
    hex_str = "".join(bytes_list)
    return hex_str
# print(combine_hex("ef cd ab 90 78 56 34 12"))  # output: '1234567890abcdef'

# replace memory addresses in a model data structure
def replace_memory(listAddr, listMem, model_data):
    max_row = len(model_data) - 1

    for row in range(1, len(model_data)):
        current_row = model_data[row]
        addr = current_row[0]
        addr_next = model_data[row + 1][0] if row != max_row else None

        for i in range(len(listAddr)):
            target_addr = listAddr[i]
            target_mem = listMem[i]

            if int(target_addr, 16) == int(addr, 16):
                print(f"Set row {row}, column 1 to {target_mem}")

            elif addr_next and int(addr, 16) < int(target_addr, 16) < int(addr_next, 16):
                col = ((int(target_addr, 16) - int(addr, 16)) // 4) + 1
                print(f"Set row {row}, column {col} to {target_mem}")

            elif not addr_next and int(target_addr, 16) > int(addr, 16):
                col = ((int(target_addr, 16) - int(addr, 16)) // 4) + 1
                print(f"Set row {row}, column {col} to {target_mem}")
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],  # header
#     ["0x1000", "", "", "", ""],
#     ["0x1010", "", "", "", ""],
#     ["0x1020", "", "", "", ""]
# ]
# listAddr = ["0x1000", "0x100C", "0x1018"]
# listMem = ["ABCD1234", "DEADBEEF", "CAFEBABE"]
# replace_memory(listAddr, listMem, model_data)
# print(model_data)  # should show updated memory model data

# replace_memory_byte function to update memory model data
def replace_memory_byte(model_data, listAddr, listMem):
    # convert each 32-bit hex value into 4 separate bytes (little-endian)
    for i in range(len(listMem)):
        listMem[i] = split_hex(listMem[i])  # e.g., ['EF', 'BE', 'AD', 'DE']

    # go through each row in the memory model
    for row in range(1, len(model_data)):
        current_addr = model_data[row][0]
        next_addr = model_data[row + 1][0] if row + 1 < len(model_data) else None

        for i in range(len(listAddr)):
            target_addr = listAddr[i]
            target_bytes = listMem[i]

            # match exact row address
            if int(target_addr, 16) == int(current_addr, 16):
                for j in range(4):
                    model_data[row][j + 1] = target_bytes[j]

            # if target is between current and next row address
            elif next_addr and int(current_addr, 16) < int(target_addr, 16) < int(next_addr, 16):
                col = ((int(target_addr, 16) - int(current_addr, 16)) // 4) + 1
                model_data[row][col] = target_bytes[0]

            # if target is after the last known address
            elif not next_addr and int(target_addr, 16) > int(current_addr, 16):
                col = ((int(target_addr, 16) - int(current_addr, 16)) // 4) + 1
                model_data[row][col] = target_bytes[0]

    # combine split hex values back if needed
    for i in range(len(listMem)):
        listMem[i] = combine_hex(listMem[i])
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],
#     ["0x1000", "", "", "", ""],
#     ["0x1010", "", "", "", ""]
# ]
# listAddr = ["0x1000", "0x1010"]
# listMem = ["DEADBEEF", "FEEDFACE"]

# replace_memory_byte(model_data, listAddr, listMem)
# print(model_data)

# find_one_memory function to search for a specific memory address
def find_one_memory(model_data, addr_input):
    search_value = twos_complement_to_signed(addr_input)

    for row in range(1, len(model_data)):
        addr = model_data[row][0]
        if search_value == twos_complement_to_signed(addr):
            # return the entire memory content in columns 1-4 concatenated, if you want
            mem_values = model_data[row][1:5]  # Columns 1 to 4
            return " ".join(mem_values)  # Or return mem_values if you want list

    # if not found, check if input address is less than last address, return '00'
    last_addr = model_data[-1][0]
    if search_value < twos_complement_to_signed(last_addr):
        return "00"
    return "00"

# find_one_memory_in_byte function to search for a specific byte at an address
def find_one_memory_in_byte(model_byte, addr_input):
    mem_out = "00"
    search_value = twos_complement_to_signed(addr_input)

    for row in range(1, len(model_byte)):
        addr = model_byte[row][0]
        offset = search_value - twos_complement_to_signed(addr)

        if 0 <= offset < 4:
            # Bytes stored in columns 1 to 4
            return model_byte[row][1 + offset]

    # if not found, return "00" only if addr_input is below last address
    last_addr = model_byte[-1][0]
    if search_value < twos_complement_to_signed(last_addr):
        return mem_out

    return mem_out
# # example data
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],
#     ["0x1000", "EF", "BE", "AD", "DE"],
#     ["0x1010", "CE", "FA", "ED", "FE"]
# ]
# print(find_one_memory(model_data, "0x1000"))       # output: 'EF BE AD DE'
# print(find_one_memory_in_byte(model_data, "0x1000"))  # output: 'EF'
# print(find_one_memory_in_byte(model_data, "0x1002"))  # output: 'AD'
# print(find_one_memory_in_byte(model_data, "0x1012"))  # output: 'ED'
# print(find_one_memory_in_byte(model_data, "0x1004"))  # output: '00' (not found)

# find_one_memory_in_halfword function to search for a halfword at an address
def find_one_memory_in_halfword(model_byte, addr_input):
    mem_out = "0000"
    search_value = twos_complement_to_signed(addr_input)

    for row in range(1, len(model_byte)):
        addr = model_byte[row][0]
        offset = search_value - twos_complement_to_signed(addr)

        # bytes are stored in columns 1,2,3,4
        mems = model_byte[row][1:5]  # get bytes as list like ['EF', 'BE', 'AD', 'DE']

        if offset == 0:
            # halfword from byte 1 and byte 0 (swap order)
            mem_out = mems[1] + mems[0]
            return mem_out
        elif offset == 1:
            # invalid halfword alignment (1-byte offset), returning default
            return mem_out
        elif offset == 2:
            # halfword from byte 3 and byte 2 (swap order)
            mem_out = mems[3] + mems[2]
            return mem_out
        elif offset == 3:
            # invalid halfword alignment (3-byte offset), returning default
            return mem_out

    # if not found and input address less than last address, return "0000"
    last_addr = model_byte[-1][0]
    if search_value < twos_complement_to_signed(last_addr):
        return mem_out

    return mem_out
# # example data
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],
#     ["0x1000", "EF", "BE", "AD", "DE"],
#     ["0x1010", "CE", "FA", "ED", "FE"]
# ]
# print(find_one_memory_in_halfword(model_data, "0x1000"))  # output: 'BEEF' (BE + EF)
# print(find_one_memory_in_halfword(model_data, "0x1002"))  # output: 'DEAD' (DE + AD)
# print(find_one_memory_in_halfword(model_data, "0x1001"))  # output: '0000' (invalid halfword alignment)
# print(find_one_memory_in_halfword(model_data, "0x1003"))  # output: '0000' (invalid halfword alignment)

# replace_one_memory function to update a specific memory address
def replace_one_memory(model_data, addr_input, mem_input):
    found = False
    search_value = twos_complement_to_signed(addr_input)

    max_row = len(model_data) - 1

    for row in range(1, len(model_data)):
        addr = model_data[row][0]
        addr_value = twos_complement_to_signed(addr)

        # determine next address if not last row
        if row != max_row:
            addr_next = model_data[row + 1][0]
            addr_next_value = twos_complement_to_signed(addr_next)
        else:
            addr_next = None
            addr_next_value = None

        # exact match: update first data column (Col1)
        if search_value == addr_value:
            model_data[row][1] = mem_input
            found = True
            return

        # if search_value lies between addr and next addr (non-inclusive)
        if addr_next and addr_value < search_value < addr_next_value:
            # calculate offset in multiples of 4 (words), add 1 for index after Col1
            num = int((search_value - addr_value) / 4) + 1

            # update the corresponding column
            if num < len(model_data[row]):
                model_data[row][num] = mem_input
                found = True
                return

        # if last row and search_value is greater than addr_value
        if not addr_next and search_value > addr_value:
            num = int((search_value - addr_value) / 4) + 1
            if num < len(model_data[row]):
                model_data[row][num] = mem_input
                found = True
                return

    # if not found and input address is less than last address, do nothing
    if not found:
        last_addr = model_data[-1][0]
        last_value = twos_complement_to_signed(last_addr)
        if search_value < last_value:
            return
# # example data:
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],
#     ["0x1000", "EF", "BE", "AD", "DE"],
#     ["0x1010", "CE", "FA", "ED", "FE"]
# ]
# replace_one_memory(model_data, "0x1000", "AA")  # update exact match at 0x1000
# replace_one_memory(model_data, "0x1004", "BB")  # update within first row, second data column
# print(model_data)

# replace_one_memory_byte function to update a specific byte at an address
def replace_one_memory_byte(model, addr_input, mem_input):
    # convert mem_input string like "EFBEADDE" to spaced bytes "DE AD BE EF"
    mem_input = split_hex(mem_input)

    found = False
    search_value = twos_complement_to_signed(addr_input)
    max_row = len(model) - 1

    for row in range(1, len(model)):
        addr = model[row][0]
        addr_value = twos_complement_to_signed(addr)

        # determine next row's address if it exists
        if row != max_row:
            addr_next = model[row + 1][0]
            addr_next_value = twos_complement_to_signed(addr_next)
        else:
            addr_next = None
            addr_next_value = None

        if search_value == addr_value:
            # exact match — update col 1 (index 1)
            print(f"Update row {row}, col 1 with {mem_input}")
            model[row][1] = mem_input
            found = True
            return

        if addr_next and addr_value < search_value < addr_next_value:
            # calculate which col to update (offset in 4-byte increments + 1)
            num = int((search_value - addr_value) / 4) + 1
            if num < len(model[row]):
                print(f"Update row {row}, col {num} with {mem_input}")
                model[row][num] = mem_input
                found = True
                return

        if not addr_next and search_value > addr_value:
            num = int((search_value - addr_value) / 4) + 1
            if num < len(model[row]):
                print(f"Update row {row}, col {num} with {mem_input}")
                model[row][num] = mem_input
                found = True
                return

    if not found:
        last_addr = model[-1][0]
        last_value = twos_complement_to_signed(last_addr)
        if search_value < last_value:
            print("Address below last address but not found.")
            return
    print("Address not found or no update made.")
# # Example model data:
# model_data = [
#     ["Address", "Col1", "Col2", "Col3", "Col4"],
#     ["0x1000", "EF", "BE", "AD", "DE"],
#     ["0x1010", "CE", "FA", "ED", "FE"]
# ]
# replace_one_memory_byte(model_data, "0x1000", "AABBCCDD")  # should update row 1, col 1
# replace_one_memory_byte(model_data, "0x1004", "11223344")  # should update row 1, col 2
# print(model_data)

# twos_complement_to_signed function to convert hex address to signed integer
def replace_one_memory_in_byte(model, addr_input, mem_input): pass
def replace_one_memory_in_halfword(model, addr_input, mem_input): pass
def replace_one_memory_halfword_in_byte(model, addr_input, mem_input): pass