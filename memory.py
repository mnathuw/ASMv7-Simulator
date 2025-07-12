# memory load/store logic + initialization
import re
import math
import logging
from typing import Dict, Tuple, Optional, List
from enum import Enum
from dict import line_edit_dict
import dict
from encoder import Encoder_12bit, Encoder_5bit

# core instructions
VALID_COMMAND_REGEX = re.compile(r"(MOV|LSR|LSL|AND|BIC|ORR|ORN|EOR|ADD|ADC|SUB|SBC|RSB)", re.IGNORECASE)
VALID_COMMAND_REGEX_BIT_OP_SPECIAL = re.compile(r"(AND|BIC|ORR|ORN|EOR)", re.IGNORECASE)
VALID_COMMAND_REGEX_ARITHMETIC_ADD_SUB = re.compile(r"(ADD|ADC|SUB|SBC|RSB)", re.IGNORECASE)
VALID_COMMAND_REGEX_BIT_OP = re.compile(r"(MOV|AND|BIC|ORR|ORN|EOR)", re.IGNORECASE)
VALID_COMMAND_REGEX_TEST = re.compile(r"(CMP|CMN|TST|TEQ)", re.IGNORECASE)
VALID_COMMAND_SINGLE_DATA_TRANFER = re.compile(r"(LDR|STR|LDRB|STRB)", re.IGNORECASE)
VALID_COMMAND_REGEX_MULTI = re.compile(r"(MUL|MLA|MLS|DIV)", re.IGNORECASE)
VALID_COMMAND_BRANCH = re.compile(r"(B|BL)", re.IGNORECASE)
VALID_COMMAND_STACKED = re.compile(r"(POP|PUSH)", re.IGNORECASE)
VALID_COMMAND_SATURATE = re.compile(r"(SSAT|USAT)", re.IGNORECASE)
VALID_COMMAND_REVERSE = re.compile(r"(REV|RBIT)", re.IGNORECASE)

# supporting condition flags, shifts, and operand formats
CONDITIONAL_MODIFIER_REGEX = re.compile(r"(EQ|NE|GE|LT|GT|LE|AL)", re.IGNORECASE)
SHIFT_REGEX = re.compile(r"(LSL|LSR)", re.IGNORECASE)
FLAG_REGEX = re.compile(r"S", re.IGNORECASE)

# operand matchers
regex_register = re.compile(r"r\d+$|lr", re.IGNORECASE)
regex_const = re.compile(r"#-?\d+$")
regex_const_hex = re.compile(r"^#0x[0-9a-fA-F]+$")

# instruction parser and helper filters
def split_and_filter(line):
    # remove leading/trailing spaces
    line = line.strip()
    # replace commas with spaces to unify separators
    line = line.replace(',', ' ')
    # split by whitespace
    parts = line.split()
    return parts
# print(split_and_filter("MOV r0, #1, S"))  # ['MOV', 'r0', '#1', 'S']

# memory-related helpers
def check_memory(self, line, address, lines, data_labels):
    condition = "al"
    memory = ""
    parts = split_and_filter(line)
    if parts is None:
         return memory
    if len(parts) < 3:
        return memory
    instruction = parts[0]
    reg = parts[1]
    mem = parts[2:]
    num_memory = ""
    reg_memory = []

    if not regex_register.match(reg):
        return memory

    if regex_register.match(reg) and (reg.lower() == "r13" or reg.lower() == "r15"):
        return memory

    if len(mem) > 4:
        return memory

    match_instruction = re.search(VALID_COMMAND_REGEX, instruction)
    match_instruction_test = re.search(VALID_COMMAND_REGEX_TEST, instruction)
    match_instruction_single_data_tranfer = re.search(VALID_COMMAND_SINGLE_DATA_TRANFER, instruction)
    match_instruction_multi = re.search(VALID_COMMAND_REGEX_MULTI, instruction)
    match_instruction_saturate = re.search(VALID_COMMAND_SATURATE, instruction)
    match_instruction_reverse = re.search(VALID_COMMAND_REVERSE, instruction)
    if match_instruction:
        instruction_clean = match_instruction.group(0)
        instruction = re.sub(match_instruction.group(0), "", instruction)
        match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
        if match_condition:
            condition = match_condition.group(0)
            instruction = re.sub(condition, "", instruction)
        match_flag = re.search(FLAG_REGEX, instruction)
        flag = "0"
        if match_flag:
            instruction = instruction.lstrip(match_flag.group(0))
            flag = "1"
        if not instruction:
            imm1 = "0"
            imm2 = "00"
            imm3 = "000"
            imm8 = "00000000"
            type = "00"
            Immediate_Operand = "0"
            if SHIFT_REGEX.match(instruction_clean):
                Rm = "0000"
                Rn = "0000"
                if len(mem) == 2:
                    if regex_register.match(mem[0]):
                        Rm = dict.register_memory_dict.get(mem[0])
                    else:
                        return memory
                    if instruction_clean.lower() == "rrx":
                        type = dict.shift_memory_dict.get(instruction_clean.lower())
                        Immediate_Operand = "1"
                    elif not instruction_clean.lower() == "rrx":
                        if regex_const.match(mem[1]):
                            clean_num = mem[1].lstrip('#')
                            num = int(clean_num)
                            num_bin = format(num, '05b')
                            imm3 = num_bin[:3]
                            imm2 = num_bin[3:]
                            Immediate_Operand = "1"
                        elif regex_const_hex.match(mem[1]):
                            clean_num = mem[1].lstrip('#')
                            num = dict.twos_complement_to_signed(clean_num)
                            num_bin = format(num, '05b')
                            imm3 = num_bin[:3]
                            imm2 = num_bin[3:]
                            Immediate_Operand = "1"
                        elif regex_register.match(mem[1]):
                            Rm = dict.register_memory_dict.get(mem[1])
                            Immediate_Operand = "0"
                        else:
                            return memory
                else:
                    return memory
                Rd = dict.register_memory_dict.get(reg)
                opcode_memory = "1101"
                if Immediate_Operand == "0":
                    memory = "111" + "1101" + "0" + "0" + type + flag + Rn + "1111" + Rd + "0000" + Rm
                elif Immediate_Operand == "1":
                    Rn = "1111"
                    memory = "111" + "0101" + "0010" + flag + Rn + "0" + imm3 + Rd + imm2 + type + Rm
            else:
                if len(mem) == 1 and (VALID_COMMAND_REGEX_BIT_OP_SPECIAL.match(instruction_clean) or VALID_COMMAND_REGEX_ARITHMETIC_ADD_SUB.match(instruction_clean)):
                    mem.append(reg)
                    mem.reverse()
                for i in range(len(mem)):
                    item = mem[i]
                    if regex_const.match(item):
                        clean_num = item.lstrip('#')
                        num = int(clean_num)
                        imm1, imm3, imm8 = dict.find_imm8_and_rot(num)
                        Immediate_Operand = "1"
                    elif regex_const_hex.match(item):
                        clean_num = item.lstrip('#')
                        num = dict.twos_complement_to_signed(clean_num)
                        imm1, imm3, imm8 = dict.find_imm8_and_rot(num)
                        Immediate_Operand = "1"
                    elif regex_register.match(item):
                        reg_memory.append(item)
                        Immediate_Operand = "0"
                        if i + 1 < len(mem) and SHIFT_REGEX.match(mem[i + 1]) and not SHIFT_REGEX.match(instruction_clean):
                            if mem[i + 1].lower() == "rrx":
                                type = dict.shift_memory_dict.get(mem[i + 1])
                                break
                            elif not mem[i + 1].lower() == "rrx" and i + 2 < len(mem):
                                if regex_const.match(mem[i + 2]):
                                    clean_num = mem[i + 2].lstrip('#')
                                    num = int(clean_num)
                                    num_bin = format(num, '05b')
                                    imm3 = num_bin[:3]
                                    imm2 = num_bin[3:]
                                    break
                            else:
                                return memory
                    else:
                        return memory
                Rd = dict.register_memory_dict.get(reg)
                Rn = "0000"
                Rm = "0000"
                if len(reg_memory) == 1:
                    Rn = dict.register_memory_dict.get(reg_memory[0])
                elif len(reg_memory) == 2:
                    Rn = dict.register_memory_dict.get(reg_memory[0])
                    Rm = dict.register_memory_dict.get(reg_memory[1])
                opcode_memory = dict.data_opcode_memory_dict.get(instruction_clean)
                if Immediate_Operand == "0":
                    memory = "11101" + '01' + opcode_memory + flag + Rn + "0" + imm3 + Rd + imm2 + type + Rm
                elif Immediate_Operand == "1":
                    memory = "11110" + imm1 + "0" + opcode_memory + flag + Rn + "0" + imm3 + Rd + imm8
        else:
            return memory
        return memory

    elif match_instruction_test:
        instruction_clean = match_instruction_test.group(0)
        instruction = re.sub(match_instruction_test.group(0), "", instruction)
        match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
        if match_condition:
            condition = match_condition.group(0)
            instruction = re.sub(condition, "", instruction)
        if not instruction:
            imm1 = "0"
            imm2 = "00"
            imm3 = "000"
            imm8 = "00000000"
            type = "00"
            flag = "1"
            for i in range(len(mem)):
                item = mem[i]
                if regex_const.match(item):
                    clean_num = item.lstrip('#')
                    num = int(clean_num)
                    imm1, imm3, imm8 = dict.find_imm8_and_rot(num)
                    Immediate_Operand = "1"
                elif regex_const_hex.match(item):
                    clean_num = item.lstrip('#')
                    num = dict.twos_complement_to_signed(clean_num)
                    imm1, imm3, imm8 = dict.find_imm8_and_rot(num)
                    Immediate_Operand = "1"
                elif regex_register.match(item):
                    reg_memory.append(item)
                    Immediate_Operand = "0"
                    if i + 1 < len(mem) and SHIFT_REGEX.match(mem[i + 1]):
                        if mem[i + 1].lower() == "rrx":
                            type = dict.shift_memory_dict.get(mem[i + 1])
                            break
                        elif not mem[i + 1].lower() == "rrx" and i + 2 < len(mem):
                            if regex_const.match(mem[i + 2]):
                                clean_num = mem[i + 2].lstrip('#')
                                num = int(clean_num)
                                num_bin = format(num, '05b')
                                imm3 = num_bin[:3]
                                imm2 = num_bin[3:]
                                break
                            else:
                                return memory
                        else:
                            return memory
                else:
                    return memory
            Rd = dict.register_memory_dict.get(reg)
            Rn = "0000"
            Rm = "0000"
            if len(reg_memory) == 1:
                Rm = reg_memory[0]
            elif len(reg_memory) == 2:
                Rn = dict.register_memory_dict.get(reg_memory[0])
                Rm = reg_memory[1]
            Rm = dict.register_memory_dict.get(Rm)
            opcode_memory = dict.data_opcode_memory_dict.get(instruction_clean)
            if Immediate_Operand == "0":
                memory = "11101" + '01' + opcode_memory + flag + Rn + "0" + imm3 + Rd + imm2 + type + Rm
            elif Immediate_Operand == "1":
                memory = "11110" + imm1 + "0" + opcode_memory + flag + Rn + "0" + imm3 + Rd + imm8
        else:
            return memory
        return memory

    elif match_instruction_single_data_tranfer:
        P = U = B = W = L = "0"
        size = "00"
        Rm = "0000"
        Rn = "0000"
        imm2 = "00"
        imm8 = "00000000"
        num_memory = "000000000000"
        instruction_clean = match_instruction_single_data_tranfer.group(0)
        instruction = re.sub(match_instruction_single_data_tranfer.group(0), "", instruction)
        match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
        if match_condition:
            condition = match_condition.group(0)
            instruction = re.sub(condition, "", instruction)
        if instruction.lower() == "b":
            instruction_clean = instruction_clean + "b"
        if instruction.lower() == "h":
            instruction_clean = instruction_clean + "h"
        if instruction_clean.lower() == "ldr":
            L = "1"
            size = "10"
        if instruction_clean.lower() == "str":
            L = "0"
            size = "10"
        if instruction_clean.lower() == "ldrb":
            L = "1"
            size = "00"
        if instruction_clean.lower() == "strb":
            L = "0"
            size = "00"
        if instruction_clean.lower() == "ldrh":
            L = "1"
            size = "01"
        if instruction_clean.lower() == "strh":
            L = "0"
            size = "01"
        regex_bracket_1 = re.compile(r"\[", re.IGNORECASE)
        regex_bracket_2 = re.compile(r"\]", re.IGNORECASE)
        if len(mem) == 1:
            bracket_1 = re.search(regex_bracket_1, mem[0])
            bracket_2 = re.search(regex_bracket_2, mem[0])
            regex_equal = re.compile(r"\=")
            if bracket_1 and bracket_2:
                mem[0] = mem[0].strip("[]")
                if regex_register.match(mem[0]):
                    reg_memory.append(mem[0])
                    Rn = dict.register_memory_dict.get(reg_memory[0])
            else:
                mapping = {key: value for key, value in zip(lines, address)}
                have_label = re.search(regex_equal, mem[0])
                if have_label and data_labels:
                    label = mem[0].strip('=')
                    Rn = "1111"
                    if label in data_labels:
                        index = data_labels.index(label)
                        hex_str = data_labels[index + 1]
                        num_1 = int(hex_str, 16)
                        num_2_str = mapping.get(line)
                        num_2 = int(num_2_str, 16)
                        num_memory = Encoder_12bit(num_1 - num_2)
                else:
                    return memory
            Rd = dict.register_memory_dict.get(reg)
            memory = "11111" + "00" + "0" + "1" + size + L + Rn + Rd + num_memory

        if len(mem) == 2:
            bracket_1 = re.search(regex_bracket_1, mem[0])
            bracket_2 = re.search(regex_bracket_2, mem[0])
            if bracket_1 and bracket_2:
                mem[0] = mem[0].strip("[]")
                W = "1"
                P = "0"
                if regex_register.match(mem[0]):
                    reg_memory.append(mem[0])
                    if regex_const.match(mem[1]):
                        clean_num = mem[1].lstrip('#')
                        num = int(clean_num)
                        if num >= 0:
                            U = "1"
                        elif num < 0:
                            U = "0"
                        imm8 = format(num, "08b")
                    else:
                        return memory
                elif not regex_register.match(mem[0]):
                    return memory

            elif bracket_1 and not bracket_2:
                mem[0] = mem[0].strip("[")
                P = "1"
                if regex_register.match(mem[0]):
                    reg_memory.append(mem[0])
                elif not regex_register.match(mem[0]):
                    return memory
                bracket_mem = re.search(regex_bracket_2, mem[1])
                if bracket_mem:
                    mem[1] = mem[1].replace("]", '')
                    exclamation = re.compile(r"\!")
                    exclamation_check = re.search(exclamation, mem[1])
                    if exclamation_check:
                        W = "1"
                        mem[1] = mem[1].strip('!')
                        if regex_const.match(mem[1]):
                            clean_num = mem[1].lstrip('#')
                            num = int(clean_num)
                            if num >= 0:
                                num_memory = Encoder_12bit(num)
                                memory = "11111" + "00" + "0" + "1" + size + L + Rn + Rd + num_memory
                                return memory
                            elif num < 0:
                                U = "0"
                            imm8 = format(num, "08b")
                        elif regex_register.match(mem[1]):
                            Rm = dict.register_memory_dict.get(mem[1])
                            memory = "11111" + "00" + "0" + "1" + size + L + Rn + Rd + "0" + "00000" + imm2 + Rm
                            return memory
                        else:
                            return memory
                    elif not exclamation_check:
                        W = "0"
                        if regex_const.match(mem[1]):
                            clean_num = mem[1].lstrip('#')
                            num = int(clean_num)
                            if num >= 0:
                                U = "1"
                            elif num < 0:
                                U = "0"
                            imm8 = format(num, "08b")
                        elif regex_const_hex.match(mem[1]):
                            clean_num = mem[1].lstrip('#')
                            num = dict.twos_complement_to_signed(clean_num)
                            if num >= 0:
                                U = "1"
                            elif num < 0:
                                U = "0"
                            imm8 = format(num, "08b")
                        elif regex_register.match(mem[1]):
                            U = "1"
                            Rm = dict.register_memory_dict.get(mem[1])
                        else:
                            return memory
                elif not bracket_mem:
                    return memory
            elif not bracket_1:
                return memory
            Rd = dict.register_memory_dict.get(reg)
            Rn = dict.register_memory_dict.get(reg_memory[0])
            memory = "11111" + "00" + "0" + "0" + size + L + Rn + Rd + "1" + P + U + W + imm8

        elif len(mem) == 4:
            bracket_1 = re.search(regex_bracket_1, mem[0])
            bracket_2 = re.search(regex_bracket_2, mem[0])
            if bracket_1 and not bracket_2:
                mem[0] = mem[0].strip("[")
                P = "1"
                if regex_register.match(mem[0]):
                    reg_memory.append(mem[0])
                elif not regex_register.match(mem[0]):
                    return memory
                search = re.search(regex_bracket_2, mem[3])
                if search:
                    mem[3] = mem[3].strip("]")
                else:
                    return memory
                for i in range(1, len(mem)):
                    item = mem[i]
                    if regex_register.match(item):
                        Rm = dict.register_memory_dict.get(item)
                        if mem[i + 1].lower() == "lsl" and i + 2 < len(mem):
                            if regex_const.match(mem[i + 2]):
                                clean_num = mem[i + 2].lstrip('#')
                                num = int(clean_num)
                                imm2 = format(num, "02b")
                                break
                    else:
                        return memory
            else:
                return memory
            U = "1"
            Rd = dict.register_memory_dict.get(reg)
            Rn = dict.register_memory_dict.get(reg_memory[0])
            memory = "11111" + "00" + "0" + "0" + size + L + Rn + Rd + "0" + "00000" + imm2 + Rm
        elif len(mem) > 4:
            return memory
        return memory

    elif match_instruction_multi:
        u = None
        if instruction and instruction[0] == "u":
            u = "0"
            instruction = instruction[1:]
        if instruction and instruction[0] == "s":
            u = "1"
            instruction = instruction[1:]
        instruction_clean = match_instruction_multi.group(0)
        instruction = re.sub(match_instruction_multi.group(0), "", instruction)
        LONG_REGEX = re.compile(r"L", re.IGNORECASE)
        l = None
        long_flag = re.search(LONG_REGEX, instruction)
        if long_flag:
            instruction = instruction.lstrip(long_flag.group(0))
            l = 1
        match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
        if match_condition:
            condition = match_condition.group(0)
            instruction = re.sub(condition, "", instruction)
        match_flag = re.search(FLAG_REGEX, instruction)
        flag = "0"
        if match_flag:
            instruction = instruction.lstrip(match_flag.group(0))
            flag = "1"
        if not instruction:
            if len(mem) == 1:
                mem.append(reg)
                mem.reverse()
            if l == 1 and len(mem) == 3:
                reg_memory.append(mem[0])
                mem = mem[1:]
            for i in range(len(mem)):
                item = mem[i]
                if regex_register.match(item):
                    reg_memory.append(item)
                else:
                    return memory
            reg_memory.reverse()
            if u != None and (l == 1 or instruction_clean.lower() == "div"):
                op1 = "000"
                op2 = "0000"
                if instruction_clean.lower() == "div":
                    Rd = dict.register_memory_dict.get(reg)
                    Rs = "1111"
                    Rn = dict.register_memory_dict.get(reg_memory[0])
                    Rm = dict.register_memory_dict.get(reg_memory[1])
                    if u == "0":
                        op1 = "011"
                        op2 = "1111"
                    elif u == "1":
                        op1 = "001"
                        op2 = "1111"
                    memory = "111" + "1101" + "11" + op1 + Rn + Rs + Rd + op2 + Rm
                else:
                    RdLo = dict.register_memory_dict.get(reg)
                    RdHi = dict.register_memory_dict.get(reg_memory[0])
                    Rn = dict.register_memory_dict.get(reg_memory[1])
                    Rm = dict.register_memory_dict.get(reg_memory[2])
                    if instruction_clean.lower() == "mla":
                        if u == "0":
                            op1 = "110"
                            op2 = "0000"
                        elif u == "1":
                            op1 = "100"
                            op2 = "0000"
                    elif instruction_clean.lower() == "mul":
                        if u == "0":
                            op1 = "010"
                            op2 = "0000"
                        elif u == "1":
                            op1 = "000"
                            op2 = "0000"
                    memory = "111" + "1101" + "11" + op1 + Rn + RdLo + RdHi + op2 + Rm
            else:
                Rd = dict.register_memory_dict.get(reg)
                Ra = "0000"
                if instruction_clean.lower() == "mls":
                    A = "1"
                    Rn = dict.register_memory_dict.get(reg_memory[0])
                    Rm = dict.register_memory_dict.get(reg_memory[1])
                    Ra = dict.register_memory_dict.get(reg_memory[2])
                else:
                    A = "0"
                    Rn = dict.register_memory_dict.get(reg_memory[0])
                    Rm = dict.register_memory_dict.get(reg_memory[1])
                memory = "11111" + "0110" + "000" + Rn + Ra + Rd + "000" + A + Rm
        else:
            return memory
        return memory

    elif match_instruction_saturate:
        instruction_clean = match_instruction_saturate.group(0)
        instruction = re.sub(match_instruction_saturate.group(0), "", instruction)
        match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
        if match_condition:
            condition = match_condition.group(0)
            instruction = re.sub(condition, "", instruction)
        shift_imm5 = "00000"
        imm3 = "000"
        imm2 = "00"
        sh = "0"
        if not instruction:
            if instruction_clean.lower() == "ssat":
                sat_num = 1
                u = "0"
            elif instruction_clean.lower() == "usat":
                sat_num = 0
                u = "1"
            Rd = dict.register_memory_dict.get(reg)
            if len(mem) == 2:
                const = mem[0]
                reg_const = mem[1]
                if regex_const.match(const) and regex_register.match(reg_const):
                    const = const.lstrip('#')
                    const = int(const) - sat_num
                    sat = Encoder_5bit(const)
                    imm3 = sat[:3]
                    imm2 = sat[3:]
                    Rn = dict.register_memory_dict.get(reg_const)
                    memory = "11110" + "0" + "11" + u + "0" + sh + "0" + Rn + "0" + imm3 + Rd + imm2 + "0" + shift_imm5
                else:
                    return memory
            elif len(mem) == 3 or len(mem) == 4:
                const = mem[0]
                reg_const = mem[1]
                shift = mem[2]
                if regex_const.match(const) and regex_register.match(reg_const):
                    const = const.lstrip('#')
                    const = int(const) - sat_num
                    sat = Encoder_5bit(const)
                    imm3 = sat[:3]
                    imm2 = sat[3:]
                    Rn = dict.register_memory_dict.get(reg_const)
                    if SHIFT_REGEX.match(shift):
                        if shift.lower() == "rrx":
                            shift_imm5 = "00000"
                        elif not shift.lower() == "rrx" and i + 2 < len(mem):
                            if regex_const.match(mem[3]):
                                clean_num = mem[3].lstrip('#')
                                num = int(clean_num)
                                shift_imm5 = Encoder_5bit(num)
                            elif regex_register.match(mem[3]):
                                num_edit = line_edit_dict.get(mem[3])
                                num_str = num_edit.text()
                                num = int(num_str, 16)
                                shift_imm5 = Encoder_5bit(num)
                    memory = "11110" + "0" + "11" + u + "0" + sh + "0" + Rn + "0" + imm3 + Rd + imm2 + "0" + shift_imm5
                else:
                    return memory
            else:
                return memory
        else:
            return memory
        return memory
    elif match_instruction_reverse:
        instruction_clean = match_instruction_reverse.group(0)
        instruction = re.sub(match_instruction_reverse.group(0), "", instruction)
        match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
        if match_condition:
            condition = match_condition.group(0)
            instruction = re.sub(condition, "", instruction)
        if not instruction:
            memory = format(0, '32b')
            if len(mem) == 1:
                if regex_register.match(mem[0]):
                    Rd = dict.register_memory_dict.get(reg)
                    Rm = dict.register_memory_dict.get(mem[0])
                    if instruction_clean.lower() == "rev":
                        memory = "11111" + "010" + "1" + "001" + Rm + "1111" + Rd + "1" + "000" + Rm
                    if instruction_clean.lower() == "rbit":
                        memory = "11111" + "010" + "1" + "001" + Rm + "1111" + Rd + "1" + "010" + Rm
                else:
                    return memory
            else:
                return memory
        else:
            return memory
        return memory
    else:
        return memory

def memory_branch(self, line, lines, address, labels):
    condition = "al"
    memory = ""
    parts = split_and_filter(line)
    if parts is None or (not len(parts) == 2):
        return memory
    instruction = parts[0]
    match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
    if match_condition:
        condition = match_condition.group(0)
        instruction = re.sub(condition, "", instruction)
    if VALID_COMMAND_BRANCH.match(instruction):
        condition_memory = dict.condition_memory_dict.get(condition)
        if instruction.lower() == "bx":
            if regex_register.match(parts[1]):
                Rn = dict.register_memory_dict.get(parts[1])
            else:
                return memory
            memory = condition_memory + "0001" + "0010" + "1111" + "1111" + "1111" + "0001" + Rn
        else:
            offset = get_memory_offset(line, parts[1], lines, address, labels)
            S = offset[0]
            J2 = offset[1]
            J1 = offset[2]
            imm6 = offset[3:9]
            imm11 = offset[9:]
            if instruction.lower() == "b":
                L = "0"
            elif instruction.lower() == "bl":
                L = "1"
            memory = "11110" + S + condition_memory + imm6 + "1" + L + J1 + "0" + J2 + imm11
        return memory
    else:
        return memory

def get_memory_offset(current_line, current_label, lines, address, labels):
    current = target = None
    result_str = "00000000000000000000"
    mapping = {key: value for key, value in zip(lines, address)}
    if current_label in labels:
        target = mapping.get(labels[current_label][0])
    current = mapping.get(current_line)
    if current != None and target != None:
        current_int = dict.twos_complement_to_signed(current)
        target_int = dict.twos_complement_to_signed(target)
        result = int((target_int - current_int - 8) / 4)
        result_str = Encoder_20bit(result)
    return result_str

# binary encoding helpers
def Encoder_20bit(number):
    if number >= 0:
        binary_str = bin(number)[2:].zfill(20)
    else:
        binary_str = bin((1 << 20) + number)[2:].zfill(20)
    if len(binary_str) > 20:
        binary_str = binary_str[-20:]
    return binary_str

def memory_stacked(self, line, lines, address, labels):
    condition = "al"
    memory = ""
    parts = split_and_filter(line)
    instruction = parts[0]
    mems = parts[1:]
    match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
    if match_condition:
        condition = match_condition.group(0)
        instruction = re.sub(condition, "", instruction)
    if VALID_COMMAND_STACKED.match(instruction):
        registers = {
                        "r0": "0", "r1": "0", "r2": "0", "r3": "0",
                        "r4": "0", "r5": "0", "r6": "0", "r7": "0",
                        "r8": "0", "r9": "0", "r10": "0", "r11": "0",
                        "r12": "0", "sp": "0", "lr": "0", "pc": "0"
                    }
        if instruction.lower() == "push":
            if mems[0].startswith("{") and mems[-1].endswith("}"):
                mems[0] = mems[0].strip('{')
                mems[-1] = mems[-1].strip('}')
                if len(mems) == 1:
                    Rt = dict.register_memory_dict.get(mems[0])
                    push = "11111" + "00" + "0" + "0" + "10" + "0" + "1101"
                    memory = push + Rt + "1" + "101" + "00000100"
                else:
                    push = "11101" + "00" + "100" + "1" + "0" + "1101"
                    for mem in mems:
                        if regex_register.match(mem):
                            if mem in registers:
                                registers[mem] = "1"
                        else:
                            return memory
                    memory = push + ("0" + registers["lr"] + "0" + registers["r12"] + registers["r11"] + registers["r10"]
                                    + registers["r9"] + registers["r8"] + registers["r7"]
                                    + registers["r6"] + registers["r5"] + registers["r4"]
                                    + registers["r3"] + registers["r2"] + registers["r1"] + registers["r0"])
            else:
                return memory

        if instruction.lower() == "pop":
            if mems[0].startswith("{") and mems[-1].endswith("}"):
                mems[0] = mems[0].strip('{')
                mems[-1] = mems[-1].strip('}')
                if len(mems) == 1:
                    Rt = dict.register_memory_dict.get(mems[0])
                    pop = "11111" + "00" + "0" + "0" + "10" + "1" + "1101"
                    memory = pop + Rt + "1" + "011" + "00000100"
                else:
                    pop = "11101" + "00" + "010" + "1" + "1" + "1101"
                    for mem in mems:
                        if regex_register.match(mem) or mem == "pc":
                            if mem in registers:
                                registers[mem] = "1"
                        else:
                            return memory
                    memory = pop + (registers["pc"] + registers["lr"] + "0" + registers["r12"] + registers["r11"] + registers["r10"]
                                    + registers["r9"] + registers["r8"] + registers["r7"]
                                    + registers["r6"] + registers["r5"] + registers["r4"]
                                    + registers["r3"] + registers["r2"] + registers["r1"] + registers["r0"])
            else:
                return memory
        return memory


# ============================================================================
# MEMORY HIERARCHY IMPLEMENTATION
# Merged from memory_hierarchy.py
# ============================================================================

class CacheType(Enum):
    """Cache mapping types"""
    DIRECT = "direct"
    FULLY_ASSOCIATIVE = "fully_associative"
    SET_ASSOCIATIVE = "set_associative"

class CacheBlock:
    """Represents a cache block/line"""

    def __init__(self, block_size: int):
        self.block_size = block_size
        self.valid = False
        self.dirty = False
        self.tag = 0
        self.data = bytearray(block_size)
        self.lru_counter = 0  # For LRU replacement in fully associative

    def is_hit(self, tag: int) -> bool:
        """Check if this block contains the requested tag"""
        return self.valid and self.tag == tag

    def load_block(self, tag: int, address: int, main_memory: 'MainMemory'):
        """Load a block from main memory"""
        self.valid = True
        self.dirty = False
        self.tag = tag

        # Calculate block start address
        block_start = (address // self.block_size) * self.block_size

        # Load data from main memory
        self.data = main_memory.read_block(block_start, self.block_size)

    def write_byte(self, offset: int, value: int):
        """Write a byte to the block"""
        if 0 <= offset < self.block_size:
            self.data[offset] = value & 0xFF
            self.dirty = True

    def read_byte(self, offset: int) -> int:
        """Read a byte from the block"""
        if 0 <= offset < self.block_size:
            return self.data[offset]
        return 0

class Cache:
    """Generic cache implementation"""

    def __init__(self, size: int, block_size: int, cache_type: CacheType, name: str, associativity: int = 1):
        self.size = size
        self.block_size = block_size
        self.cache_type = cache_type
        self.name = name

        # Calculate cache parameters
        self.num_blocks = size // block_size
        if cache_type == CacheType.DIRECT:
            self.num_sets = self.num_blocks
            self.associativity = 1
        elif cache_type == CacheType.FULLY_ASSOCIATIVE:
            self.num_sets = 1
            self.associativity = self.num_blocks
        else:  # SET_ASSOCIATIVE
            self.associativity = min(associativity, self.num_blocks)  # Ensure valid associativity
            self.num_sets = self.num_blocks // self.associativity

        # Initialize cache blocks
        self.blocks = []
        for i in range(self.num_sets):
            set_blocks = [CacheBlock(block_size) for _ in range(self.associativity)]
            self.blocks.append(set_blocks)

        # Statistics
        self.hits = 0
        self.misses = 0
        self.write_backs = 0
        self.accesses = 0

        # LRU tracking for fully associative
        self.lru_counter = 0

        self.logger = logging.getLogger(f"Cache.{name}")

    def _get_cache_indices(self, address: int) -> Tuple[int, int, int]:
        """Get set index, tag, and block offset from address"""
        block_offset = address % self.block_size
        block_address = address // self.block_size

        if self.cache_type == CacheType.DIRECT:
            set_index = block_address % self.num_sets
            tag = block_address // self.num_sets
        elif self.cache_type == CacheType.FULLY_ASSOCIATIVE:
            set_index = 0
            tag = block_address
        else:  # SET_ASSOCIATIVE
            set_index = block_address % self.num_sets
            tag = block_address // self.num_sets

        return set_index, tag, block_offset

    def _find_block_in_set(self, set_blocks: List[CacheBlock], tag: int) -> Optional[CacheBlock]:
        """Find a block with the given tag in a set"""
        for block in set_blocks:
            if block.is_hit(tag):
                return block
        return None

    def _find_replacement_block(self, set_blocks: List[CacheBlock]) -> CacheBlock:
        """Find a block to replace using LRU policy"""
        # First try to find an invalid block
        for block in set_blocks:
            if not block.valid:
                return block

        # If all blocks are valid, use LRU
        lru_block = min(set_blocks, key=lambda b: b.lru_counter)
        return lru_block

    def _update_lru(self, block: CacheBlock):
        """Update LRU counter for the accessed block"""
        self.lru_counter += 1
        block.lru_counter = self.lru_counter

    def access(self, address: int, is_write: bool, value: Optional[int] = None,
               main_memory: 'MainMemory' = None, next_level: 'Cache' = None) -> bool:
        """
        Access the cache for read or write
        Returns True if hit, False if miss
        """
        self.accesses += 1
        set_index, tag, block_offset = self._get_cache_indices(address)
        set_blocks = self.blocks[set_index]

        # Look for the block in the set
        block = self._find_block_in_set(set_blocks, tag)

        if block is not None:
            # Cache hit
            self.hits += 1
            self._update_lru(block)

            if is_write and value is not None:
                block.write_byte(block_offset, value)

            self.logger.debug(f"HIT: {self.name} address=0x{address:08X}")
            return True
        else:
            # Cache miss
            self.misses += 1
            self.logger.debug(f"MISS: {self.name} address=0x{address:08X}")

            # Find a block to replace
            replacement_block = self._find_replacement_block(set_blocks)

            # Write back if dirty
            if replacement_block.valid and replacement_block.dirty:
                self.write_backs += 1
                # Calculate original address of the dirty block
                if self.cache_type == CacheType.DIRECT:
                    original_tag = replacement_block.tag
                    original_address = (original_tag * self.num_sets + set_index) * self.block_size
                else:  # FULLY_ASSOCIATIVE
                    original_address = replacement_block.tag * self.block_size

                # Write back to next level or main memory
                if next_level:
                    self._write_back_to_next_level(replacement_block, original_address, next_level, main_memory)
                elif main_memory:
                    self._write_back_to_memory(replacement_block, original_address, main_memory)

                self.logger.debug(f"WRITEBACK: {self.name} address=0x{original_address:08X}")

            # Load new block
            if next_level:
                # Try to load from next level cache first
                self._load_from_next_level(replacement_block, address, tag, next_level, main_memory)
            elif main_memory:
                # Load directly from main memory
                replacement_block.load_block(tag, address, main_memory)

            self._update_lru(replacement_block)

            # Perform the requested operation
            if is_write and value is not None:
                replacement_block.write_byte(block_offset, value)

            return False

    def _write_back_to_next_level(self, block: CacheBlock, address: int,
                                  next_level: 'Cache', main_memory: 'MainMemory'):
        """Write back dirty block to next level cache"""
        for i in range(block.block_size):
            next_level.access(address + i, True, block.data[i], main_memory)

    def _write_back_to_memory(self, block: CacheBlock, address: int, main_memory: 'MainMemory'):
        """Write back dirty block to main memory"""
        main_memory.write_block(address, block.data)

    def _load_from_next_level(self, block: CacheBlock, address: int, tag: int,
                              next_level: 'Cache', main_memory: 'MainMemory'):
        """Load block from next level cache"""
        # Load the entire block from next level
        block_start = (address // self.block_size) * self.block_size

        for i in range(self.block_size):
            next_level.access(block_start + i, False, None, main_memory)

        # Now load the block data (simplified - in reality would get data from next level)
        block.load_block(tag, address, main_memory)

    def read_byte(self, address: int, main_memory: 'MainMemory' = None,
                  next_level: 'Cache' = None) -> int:
        """Read a byte from cache"""
        set_index, tag, block_offset = self._get_cache_indices(address)

        # Access the cache (this handles miss/hit logic)
        hit = self.access(address, False, None, main_memory, next_level)

        # Get the block and return the byte
        set_blocks = self.blocks[set_index]
        block = self._find_block_in_set(set_blocks, tag)

        if block:
            return block.read_byte(block_offset)
        return 0

    def write_byte(self, address: int, value: int, main_memory: 'MainMemory' = None,
                   next_level: 'Cache' = None):
        """Write a byte to cache"""
        self.access(address, True, value, main_memory, next_level)

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        hit_rate = (self.hits / self.accesses) if self.accesses > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'write_backs': self.write_backs,
            'accesses': self.accesses,
            'hit_rate': hit_rate
        }

    def reset_stats(self):
        """Reset cache statistics"""
        self.hits = 0
        self.misses = 0
        self.write_backs = 0
        self.accesses = 0

class MainMemory:
    """Main memory simulation"""

    def __init__(self, size: int = 1024 * 1024):  # 1MB default
        self.size = size
        self.data = bytearray(size)
        self.accesses = 0

    def read_byte(self, address: int) -> int:
        """Read a byte from memory"""
        self.accesses += 1
        if 0 <= address < self.size:
            return self.data[address]
        return 0

    def write_byte(self, address: int, value: int):
        """Write a byte to memory"""
        self.accesses += 1
        if 0 <= address < self.size:
            self.data[address] = value & 0xFF

    def read_block(self, address: int, block_size: int) -> bytearray:
        """Read a block of data from memory"""
        end_addr = min(address + block_size, self.size)
        return self.data[address:end_addr]

    def write_block(self, address: int, data: bytearray):
        """Write a block of data to memory"""
        end_addr = min(address + len(data), self.size)
        self.data[address:end_addr] = data[:end_addr - address]

    def load_program(self, program_data: bytes, start_address: int = 0):
        """Load program data into memory"""
        end_addr = min(start_address + len(program_data), self.size)
        self.data[start_address:end_addr] = program_data[:end_addr - start_address]

class MemoryHierarchy:
    """Complete memory hierarchy with L1, L2 caches and main memory"""

    def __init__(self, l1_block_size: int = 16, l2_block_size: int = 32,
                 l1_cache_type: str = 'direct', l1_associativity: int = 1,
                 l1_size: int = 1024, l2_size: int = 16384):

        # Create main memory
        self.main_memory = MainMemory()

        # Determine cache type and associativity
        if l1_cache_type == 'direct':
            cache_type = CacheType.DIRECT
            associativity = 1
        elif l1_cache_type == 'fully_associative':
            cache_type = CacheType.FULLY_ASSOCIATIVE
            associativity = l1_size // l1_block_size  # All blocks in one set
        else:  # set_associative or any other value
            cache_type = CacheType.SET_ASSOCIATIVE
            associativity = l1_associativity

        # Create L2 cache (unified, direct-mapped for simplicity)
        self.l2_cache = Cache(
            size=l2_size,
            block_size=l2_block_size,
            cache_type=CacheType.DIRECT,
            name="L2"
        )

        # Create L1 caches (separate instruction and data)
        self.l1_icache = Cache(
            size=l1_size,
            block_size=l1_block_size,
            cache_type=cache_type,
            name="L1I",
            associativity=associativity
        )

        self.l1_dcache = Cache(
            size=l1_size,
            block_size=l1_block_size,
            cache_type=cache_type,
            name="L1D",
            associativity=associativity
        )

        self.logger = logging.getLogger("MemoryHierarchy")

    def read_instruction(self, address: int) -> int:
        """Read instruction from memory hierarchy"""
        return self.l1_icache.read_byte(address, self.main_memory, self.l2_cache)

    def read_data(self, address: int) -> int:
        """Read data from memory hierarchy"""
        return self.l1_dcache.read_byte(address, self.main_memory, self.l2_cache)

    def write_data(self, address: int, value: int):
        """Write data to memory hierarchy"""
        self.l1_dcache.write_byte(address, value, self.main_memory, self.l2_cache)

    def read_word(self, address: int, is_instruction: bool = False) -> int:
        """Read a 32-bit word from memory"""
        word = 0
        for i in range(4):
            if is_instruction:
                byte_val = self.read_instruction(address + i)
            else:
                byte_val = self.read_data(address + i)
            word |= (byte_val << (i * 8))
        return word

    def write_word(self, address: int, value: int):
        """Write a 32-bit word to memory"""
        for i in range(4):
            byte_val = (value >> (i * 8)) & 0xFF
            self.write_data(address + i, byte_val)

    def load_program(self, program_data: bytes, start_address: int = 0):
        """Load program into main memory"""
        self.main_memory.load_program(program_data, start_address)

    def get_statistics(self) -> Dict[str, any]:
        """Get comprehensive memory hierarchy statistics"""
        l1i_stats = self.l1_icache.get_stats()
        l1d_stats = self.l1_dcache.get_stats()
        l2_stats = self.l2_cache.get_stats()

        total_l1_misses = l1i_stats['misses'] + l1d_stats['misses']
        total_write_backs = (l1i_stats['write_backs'] +
                            l1d_stats['write_backs'] +
                            l2_stats['write_backs'])

        # Calculate cost function
        cost = 0.5 * total_l1_misses + l2_stats['misses'] + total_write_backs

        return {
            'l1_icache': l1i_stats,
            'l1_dcache': l1d_stats,
            'l2_cache': l2_stats,
            'total_l1_misses': total_l1_misses,
            'total_write_backs': total_write_backs,
            'cost': cost,
            'memory_accesses': self.main_memory.accesses
        }

    def reset_statistics(self):
        """Reset all cache statistics"""
        self.l1_icache.reset_stats()
        self.l1_dcache.reset_stats()
        self.l2_cache.reset_stats()
        self.main_memory.accesses = 0

