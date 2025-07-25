import re
import string
from encoder import Encoder
from decoder import Decoder
import dict
from PyQt6 import QtWidgets

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

def is_special_or_digit(word):
    if not word:
        return False
    first_char = word[0]
    if first_char.isdigit():
        return True
    special_characters = string.punctuation
    if first_char in special_characters:
        return True
    return False

def parse_data(lines):
    original_list = []
    data_lines = []
    if VALID_DATA in lines or VALID_TEXT in lines:
        if VALID_DATA in lines and not VALID_TEXT in lines:
            index_data = lines.index(VALID_DATA)
            original_list = lines[:index_data]
            data_lines = lines[index_data:]
        elif not VALID_DATA in lines and VALID_TEXT in lines:
            index_text = lines.index(VALID_TEXT)
            original_list = lines[index_text + 1:]
        elif VALID_DATA in lines and VALID_TEXT in lines:
            index_text = lines.index(VALID_TEXT)
            index_data = lines.index(VALID_DATA)

            # Extract text section (instructions)
            if index_text < index_data:
                # .text comes before .data
                for i in range(index_text + 1, index_data):
                    if not lines[i].startswith('.'):
                        original_list.append(lines[i])
                    else:
                        break
            else:
                # .data comes before .text
                for i in range(index_text + 1, len(lines)):
                    if not lines[i].startswith('.'):
                        original_list.append(lines[i])
                    else:
                        break

            # Extract data section
            data_lines.append(lines[index_data])
            start_index = index_data + 1
            end_index = index_text if index_data < index_text else len(lines)
            for i in range(start_index, end_index):
                if not lines[i].startswith('.'):
                    data_lines.append(lines[i])
                else:
                    break
        return original_list, data_lines
    else:
        return lines, []

def process_data(data_lines, address):
    label_data = []
    data_address = []
    data_memory = []

    # Check if address list is empty and provide default base address
    if not address or len(address) == 0:
        address_data_base = 0x1000  # Default data section base address
    else:
        address_data_base = int(address[-1], 16) + 4

    data_lines = [item for item in data_lines if item not in ["", None]]
    if len(data_lines) >= 2:
        data_lines = data_lines[1:]
        temp = []
        for line in data_lines:
            stripped_line = line.strip()
            result = is_special_or_digit(stripped_line)
            parts = split_and_filter(line)
            if len(parts) > 2:
                if parts[0].endswith(':') and not result and (parts[1] == VALID_SIZE or VALID_SPACE_MEMORY.match(parts[1]) or parts[1] == VALID_ASCII):
                    address_data_base_str = format(address_data_base, '08x')
                    data_address.append(address_data_base_str)
                    instruction = parts[1]
                    parts[0] = parts[0].strip(':')
                    label_data.append(parts[0])
                    label_data.append(address_data_base_str)
                    parts = parts[2:]
                    if len(parts) == 1 and instruction == VALID_SIZE:
                        label_data.append("equ")
                    address_data_base += 4
                else:
                    return None, None, None
        for line in data_lines:
            stripped_line = line.strip()
            result = is_special_or_digit(stripped_line)
            parts = split_and_filter(line)
            if len(parts) > 2:
                if parts[0].endswith(':') and not result and parts[1] == VALID_SIZE:
                    parts = parts[2:]
                    if len(parts) == 1:
                        if regex_const.match(parts[0]):
                            num = int(parts[0])
                            num_bin_str = Encoder(num)
                            num = Decoder(num_bin_str)
                            num_str = format(num, '08x')
                            data_memory.append(num_str)
                        elif regex_const_hex.match(parts[0]):
                            num = int(parts[0], 16)
                            num_str = format(num, '08x')
                            data_memory.append(num_str)
                    else:
                        for part in parts:
                            if regex_const.match(part):
                                num = int(part)
                                num_bin_str = Encoder(num)
                                num = Decoder(num_bin_str)
                                num_str = format(num, '08x')
                                temp.append(num_str)
                                data_address.append(address_data_base_str)
                            elif regex_const_hex.match(part):
                                num = int(part, 16)
                                num_str = format(num, '08x')
                                temp.append(num_str)
                                data_address.append(address_data_base_str)
                            address_data_base += 4
                            address_data_base_str = format(address_data_base, '08x')
                elif parts[0].endswith(':') and not result and VALID_SPACE_MEMORY.match(parts[1]):
                    parts = parts[2:]
                    address_data_base_str = format(address_data_base, '08x')
                    data_memory.append(address_data_base_str)
                    if len(parts) == 1:
                        try:
                            size_in_bytes = int(parts[0])
                        except ValueError:
                            QtWidgets.QMessageBox.critical(None, "Error", ".space specifies non-absolute value")
                            return None, None, None
                        if size_in_bytes % 4 == 0:
                            num_addr = size_in_bytes // 4
                        else:
                            num_addr = size_in_bytes // 4 + 1
                        for i in range(num_addr):
                            num_str = format(0, '08x')
                            temp.append(num_str)
                            data_address.append(address_data_base_str)
                            address_data_base += 4
                            address_data_base_str = format(address_data_base, '08x')
                    elif len(parts) == 2:
                        try:
                            if regex_const.match(parts[0]):
                                size_in_bytes = int(parts[0])
                            elif regex_const_hex.match(parts[0]):
                                size_in_bytes = int(parts[0], 16)
                            else:
                                raise ValueError("Invalid size format")

                            if regex_const.match(parts[1]):
                                fill_value = int(parts[1])
                            elif regex_const_hex.match(parts[1]):
                                fill_value = int(parts[1], 16)
                            else:
                                raise ValueError("Invalid fill value format")
                        except ValueError:
                            QtWidgets.QMessageBox.critical(None, "Error", ".space specifies non-absolute value")
                            return None, None, None
                        if size_in_bytes % 4 == 0:
                            num_addr = size_in_bytes // 4
                        else:
                            num_addr = size_in_bytes // 4 + 1
                        for i in range(num_addr):
                            if fill_value >= -128 and fill_value <= 255:
                                # Handle negative values by converting to unsigned byte representation
                                if fill_value < 0:
                                    byte_value = fill_value & 0xFF
                                else:
                                    byte_value = fill_value
                                num_str = format(byte_value, '02x')
                                fill_value_str = num_str + num_str + num_str + num_str
                                temp.append(fill_value_str)
                            else:
                                fill_value_str = format(0, '08x')
                                temp.append(fill_value_str)
                            data_address.append(address_data_base_str)
                            address_data_base += 4
                            address_data_base_str = format(address_data_base, '08x')
                    else:
                        return None, None, None
                elif parts[0].endswith(':') and not result and parts[1] == VALID_ASCII:
                    parts = re.findall(r'"(.*?)"', line)
                    address_data_base_str = format(address_data_base, '08x')
                    data_memory.append(address_data_base_str)
                    if len(parts) > 0:
                        for i in range(len(parts)):
                            string = parts[i]
                            ascii_mem = dict.ascii_memory(string)
                            for j in range(len(ascii_mem)):
                                temp.append(ascii_mem[j])
                                data_address.append(address_data_base_str)
                                address_data_base += 4
                                address_data_base_str = format(address_data_base, '08x')
                    else:
                        return None, None, None
                else:
                    return None, None, None
            else:
                return None, None, None
        data_memory.extend(temp)
        return label_data, data_address, data_memory
    else:
        return None, None, None

