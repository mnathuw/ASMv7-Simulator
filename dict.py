# look tables (opcodes, registers, etc.)
from decoder import Decoder
from encoder import Encoder
import string

# register and condition flags
register_memory_dict = {
    "r0": '0000', "r1": '0001', "r2": '0010', "r3": '0011',
    "r4": '0100', "r5": '0101', "r6": '0110', "r7": '0111',
    "r8": '1000', "r9": '1001', "r10": '1010', "r11": '1011',
    "r12": '1100', "sp": '1101', "lr": '1110', "pc": '1111'
}

condition_memory_dict = {
    "eq": '0000', "ne": '0001', "ge": '1010', "lt": '1011',
    "gt": '1100', "le": '1101', "al": '1110'
}

shift_memory_dict = {
    "lsl": '00', "lsr": '01'
}

# Opcodes for common intructions
DataProcessing_opcode_memory_dict = {
    "add": '1000', "sub": '1101', "mov": '0010',
    "cmp": '1101', "ldr": '0101', "str": '0100',
    "b": '1010', "bl": '1011'
}

# helper functions
def twos_complement_to_signed(hex_str): pass
def add_32(temporary, line): pass
def sub_32(temporary, line): pass
def detect_overflow_add(a, b, res): pass
def detect_overflow_sub(a, b, res): pass

def l_shift_32_c(a, shift_val, line): pass
def r_shift_32_c(a, shift_val, line): pass

def find_one_memory(model, addr_input): pass
def replace_one_memory(model, addr_input, mem_input): pass
def find_one_memory_in_byte(model_byte, addr_input): pass
def replace_one_memory_byte(model, addr_input, mem_input): pass

def ascii_memory(string, group_size=4): pass
def split_hex(hex_str): pass
def combine_hex(memory): pass
