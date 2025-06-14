import re
import string
from encoder import Encoder
from decoder import Decoder
import dict

VALID_TEXT = ".text"
VALID_DATA = ".data"
VALID_SIZE = ".word"
VALID_ASCII = ".asciz"
VALID_SPACE_MEMORY = re.compile(r"(.space|.skip|.zero)", re.IGNORECASE)

regex_const = re.compile(r"-?\d+$")
regex_const_hex = re.compile(r"^0x[0-9a-fA-F]+$")

def split_and_filter(line):
    # remove leading/trailing spaces
    line = line.strip()
    # replace commas with spaces to unify separators
    line = line.replace(',', ' ')
    # split by whitespace
    parts = line.split()
    return parts
# print(split_and_filter("MOV r0, #1, S"))  # ['MOV', 'r0', '#1', 'S']

def is_special_or_digit(word):pass

def parse_data(lines):pass

def process_data(data_lines, address_start="0x1000"): pass

