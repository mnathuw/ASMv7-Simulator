# main driver tying everything together
import re
from dict import line_edit_dict, conditon_dict
import dict
from encoder import Encoder
from decoder import Decoder

# REGEX patterns for all valid intructions and operands
VALID_COMMAND_REGEX = re.compile(r"(ADD|SUB|MOV|CMP|B|BL|STR|LDR|LSL|LSR|ADDS|SUBS|MOVS|BNE|PUSH|POP)", re.IGNORECASE)
SHIFT_REGEX = re.compile(r"(LSL|LSR)", re.IGNORECASE)
CONDITIONAL_MODIFIER_REGEX = re.compile(r"(EQ|NE|GE|LT|GT|LE|AL)", re.IGNORECASE)
FLAG_REGEX = re.compile(r"S", re.IGNORECASE)

# operands regex patterns
regex_register = re.compile(r"r\d+$|lr")
regex_const = re.compile(r"#-?\d+$")
regex_const_hex = re.compile(r"^#0x[0-9a-fA-F]+$")

# function stubs to implement or keep
def split_and_filter(line):
    pass

def check_branch(self, line, address, lines):
    pass

def check_stacked(self, line, address, lines, stacked):
    pass

def check_assembly_line(self, lines, line, address, memory, data_labels, model, model_2, model_4, model_8, model_byte, model_2_byte, model_4_byte, model_8_byte, stacked):
    pass

def check_shift(temporary, instruction, line):
    pass

def check_command(temporary, instruction, line):
    pass

def check_command_with_flag(temporary, instruction, line):
    pass

def check_command_long(temporary, instruction, u, reg, line):
    pass

# intruction implementations
def ADD(temporary, line): pass
def SUB(temporary, line): pass
def MOV(temporary, line): pass
def CMP(temporary, line): pass
def B(temporary, line): pass
def BL(temporary, line): pass
def STR(temporary, line): pass
def LDR(temporary, line): pass
def LSL(temporary, line): pass
def LSR(temporary, line): pass
def ADDS(temporary, line): pass
def SUBS(temporary, line): pass
def MOVS(temporary, line): pass
def BNE(temporary, line): pass
def PUSH(temporary, line): pass
def POP(temporary, line): pass
