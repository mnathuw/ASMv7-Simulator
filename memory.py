# memory load/store logic + initialization
import re
import dict
from encoder import Encoder_12bit, Encoder_5bit

# core instructions
VALID_COMMAND_REGEX = re.compile(r"(MOV|LSR|LSL|AND|ORR|EOR|ADD|SUB|CMP|LDR|STR|B|BL|PUSH|POP)", re.IGNORECASE)
VALID_COMMAND_ARITHMETIC = re.compile(r"(ADD|SUB)", re.IGNORECASE)
VALID_COMMAND_BRANCH = re.compile(r"(B|BL)", re.IGNORECASE)
VALID_COMMAND_STACKED = re.compile(r"(PUSH|POP)", re.IGNORECASE)
VALID_COMMAND_DATA_TRANSFER = re.compile(r"(LDR|STR)", re.IGNORECASE)
VALID_COMMAND_SHIFT = re.compile(r"(LSL|LSR)", re.IGNORECASE)

# supporting condition flags, shifts, and operand formats
CONDITIONAL_MODIFIER_REGEX = re.compile(r"(EQ|NE|GE|LT|GT|LE|AL)", re.IGNORECASE)
SHIFT_REGEX = re.compile(r"(LSL|LSR)", re.IGNORECASE)
FLAG_REGEX = re.compile(r"S", re.IGNORECASE)

# operand matchers
regex_register = re.compile(r"r\d+$|lr", re.IGNORECASE)
regex_const = re.compile(r"#-?\d+$")
regex_const_hex = re.compile(r"^#0x[0-9a-fA-F]+$")

# instruction parser and helper filters
def split_and_filter(line): pass

# memory-related helpers
def check_memory(self, line, address, lines, data_labels): pass
def memory_branch(self, line, lines, address, labels): pass
def get_memory_offset(current_line, current_label, lines, address, labels): pass

# binary encoding helpers
def Encoder_20bit(number): pass
def memory_stacked(self, line, lines, address, labels): pass

