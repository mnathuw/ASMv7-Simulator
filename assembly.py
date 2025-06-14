# main driver tying everything together
import re
from dict import line_edit_dict, condition_dict, condition_memory_dict
import dict
from encoder import Encoder
from decoder import Decoder

# REGEX patterns for all valid intructions and operands
VALID_COMMAND_REGEX = re.compile(r"(MOV|MVN|LSR|LSL|ASR|ROR|RRX|AND|BIC|ORR|EOR|ADD|ADC|SUB|SBC|RSB)", re.IGNORECASE)
VALID_COMMAND_REGEX_BIT_OP = re.compile(r"(MOV|MVN|AND|BIC|ORR|ORN|EOR)", re.IGNORECASE)
VALID_COMMAND_REGEX_TEST = re.compile(r"(CMP|CMN|TST|TEQ)", re.IGNORECASE)
VALID_COMMAND_REGEX_BIT_OP_SPECIAL = re.compile(r"(AND|BIC|ORR|ORN|EOR)", re.IGNORECASE)
VALID_COMMAND_REGEX_ARITHMETIC_ADD_SUB = re.compile(r"(ADD|ADC|SUB|SBC|RSB)", re.IGNORECASE)
VALID_COMMAND_REGEX_MULTI = re.compile(r"(MUL|MLA|MLS|DIV)", re.IGNORECASE)
VALID_COMMAND_SINGLE_DATA_TRANFER = re.compile(r"(LDR|STR|LDRB|STRB)", re.IGNORECASE)
VALID_COMMAND_BRANCH = re.compile(r"(B|BL|BX)", re.IGNORECASE)
VALID_COMMAND_STACKED = re.compile(r"(POP|PUSH)", re.IGNORECASE)
VALID_COMMAND_SATURATE = re.compile(r"(SSAT|USAT)", re.IGNORECASE)
VALID_COMMAND_REVERSE = re.compile(r"(REV|RBIT)", re.IGNORECASE)
CONDITIONAL_MODIFIER_REGEX = re.compile(r"(EQ|NE|CS|HS|CC|LO|MI|PL|VS|VC|HI|LS|GE|LT|GT|LE|AL)", re.IGNORECASE)
SHIFT_REGEX = re.compile(r"(LSL|LSR|ASR|ROR|RRX)", re.IGNORECASE)
FLAG_REGEX = re.compile(r"S", re.IGNORECASE)
COLON_REGEX = re.compile(r"\:")

# operands regex patterns
regex_register = re.compile(r"r\d+$|lr")
regex_const = re.compile(r"#-?\d+$")
regex_const_hex = re.compile(r"^#0x[0-9a-fA-F]+$")

# need to fix this check_condition function in dict.py:
def check_condition(condition):
    # For testing, assume all conditions are True except invalid ones
    valid_conditions = {"eq", "ne", "cs", "hs", "cc", "lo", "mi", "pl",
                        "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al"}
    return condition.lower() in valid_conditions

# Dummy class to simulate line edit widgets for testing
class Dummy:
    def __init__(self, text):
        self._text = text
        self.style = ""
    def text(self):
        return self._text
    def setText(self, val):
        self._text = val
    def setStyleSheet(self, val):
        self.style = val

# line_edit_dict simulating register values
line_edit_dict = {
    "sp": Dummy("00001000"),
    "r0": Dummy("0000000A"),  # 10
    "r1": Dummy("00000014"),  # 20
    "r2": Dummy("0000001E"),
    "r3": Dummy("00000028"),
    "r4": Dummy("00000032"),
    "lr": Dummy("00000000"),
    "pc": Dummy("00000000"),
}

# function to split and filter line
def split_and_filter(line):
    line = line.strip()
    line = line.replace(',', ' ')
    parts = line.split()
    return parts
# print(split_and_filter("MOV r0, #1, S"))  # ['MOV', 'r0', '#1', 'S']

# check_branch analyze an ARM branch instruction
def check_branch(line, address, lines):
    flag_B = None
    condition = "al"

    # build direct lookup maps
    addr_to_line = {}
    line_to_addr = {}
    for i in range(len(address)):
        addr_to_line[address[i]] = lines[i]
        line_to_addr[lines[i]] = address[i]

    parts = split_and_filter(line)
    if not parts or len(parts) != 2:
        return None, flag_B

    instruction = parts[0]
    operand = parts[1]

    # check for conditional modifier
    match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
    if match_condition:
        condition = match_condition.group(0)
        if not dict.check_condition(condition):
            return None, flag_B
        instruction = instruction.replace(condition, "")
    else:
        if not dict.check_condition(condition):  # default is "al"
            return None, flag_B

    if not VALID_COMMAND_BRANCH.match(instruction):
        return None, flag_B

    flag_B = 1

    # handle BX
    if instruction.lower() == "bx":
        if regex_register.match(operand):
            reg_value = line_edit_dict.get(operand)
            if reg_value:
                bit_str = reg_value.text()
                bit_int = dict.twos_complement_to_signed(bit_str)
                hex_addr = format(bit_int, '08x')
                label = addr_to_line.get(hex_addr)
                return label, flag_B
        return None, None

    # handle BL
    if instruction.lower() == "bl":
        addr = line_to_addr.get(line)
        if addr:
            int_addr = dict.twos_complement_to_signed(addr)
            return_addr = format(int_addr + 4, '08x')
            lr = line_edit_dict.get("lr")
            if lr:
                lr.setText(return_addr)

    return operand, flag_B
# # sample data for testing
# address_list = ["0000000a", "0000000e", "00000012"]  # sample addresses as hex strings
# line_list = ["bx r0", "bl func", "b somewhere"]
# label, flag = check_branch("bx r0", address_list, line_list)
# print("--- BX Output:", label, flag)
# label, flag = check_branch("bl func", address_list, line_list)
# print("--- BL Output:", label, flag)
# print("--- Link Register (lr):", line_edit_dict["lr"].text())
# label, flag = check_branch("b somewhere", address_list, line_list)
# print("--- B Output:", label, flag)
# label, flag = check_branch("beq somewhere", address_list, line_list)
# print("--- BEQ Output:", label, flag)
# label, flag = check_branch("bzz somewhere", address_list, line_list)
# print("--- Invalid condition Output:", label, flag)

# check_stacked analyze ARM push/pop instructions
def check_stacked(line, address, lines, stacked):
    addr_to_line = {address[i]: lines[i] for i in range(len(address))}
    label_stacked = None
    flag_stacked = None
    reg_stacked = []
    arguments_stacked = []
    condition = "al"

    parts = split_and_filter(line)
    if not parts:
        return None, None, None, None

    instruction = parts[0]
    mems = parts[1:]

    match_condition = re.search(CONDITIONAL_MODIFIER_REGEX, instruction)
    if match_condition:
        condition = match_condition.group(0)
        c = dict.check_condition(condition)
        instruction = re.sub(condition, "", instruction)
    else:
        c = dict.check_condition(condition)

    if not c or not VALID_COMMAND_STACKED.match(instruction):
        return None, None, None, None

    sp_line = line_edit_dict.get("sp")
    sp_hex_str = sp_line.text()
    sp = twos_complement_to_signed(sp_hex_str)

    if instruction.lower() == "push":
        flag_stacked = 1
        if mems and mems[0].startswith("{") and mems[-1].endswith("}"):
            mems[0] = mems[0].strip('{')
            mems[-1] = mems[-1].strip('}')
            for mem in mems:
                mem = mem.lower()
                if regex_register.match(mem):
                    reg_line = line_edit_dict.get(mem)
                    if reg_line is None or reg_line.text() is None:
                        return None, None, None, None
                    bit_str = reg_line.text()
                    bit_int = twos_complement_to_signed(bit_str)
                    hex_string = format(bit_int & 0xFFFFFFFF, '08x')
                    stacked.append(hex_string)
                    sp -= 4
                else:
                    return None, None, None, None
        else:
            return None, None, None, None

    elif instruction.lower() == "pop":
        flag_stacked = 2
        pop_list = []
        if mems and mems[0].startswith("{") and mems[-1].endswith("}"):
            mems[0] = mems[0].strip('{')
            mems[-1] = mems[-1].strip('}')
            for mem in mems:
                mem = mem.lower()
                if regex_register.match(mem) or mem == "pc":
                    pop_list.append(mem)
                else:
                    return None, None, None, None
        else:
            return None, None, None, None

        if len(pop_list) <= len(stacked):
            mapping = {pop_list[i]: stacked[i] for i in range(len(pop_list))}
            if "pc" in pop_list:
                label_stacked = addr_to_line.get(mapping.get("pc"))
                pop_list.remove("pc")
                sp += 4
            for reg in pop_list:
                reg_stacked.append(reg)
                hex_str = mapping.get(reg)
                int_val = twos_complement_to_signed(hex_str)
                bin_str = str(Encoder(int_val))
                arguments_stacked.append(bin_str)
                sp += 4
        else:
            flag_stacked = 3
            return None, None, None, flag_stacked

    sp_bin_str = str(Encoder(sp))
    sp_dec = Decoder(sp_bin_str)
    return reg_stacked, arguments_stacked, label_stacked, flag_stacked
# # sample data for testing
# address_list = ["00001000", "00001004", "00001008"]
# line_list = ["push {r0,r1}", "pop {r1,r0}", "pop {pc}"]
# stacked_memory = []
# print("--- Testing PUSH ---")
# regs, args, label, flag = check_stacked("push {r0,r1}", address_list, line_list, stacked_memory)
# print("Registers:", regs)
# print("Arguments:", args)
# print("Label:", label)
# print("Flag:", flag)
# print("Stacked Memory:", stacked_memory)
# print("SP after push:", line_edit_dict["sp"].text())
# print()

# print("--- Testing POP ---")
# regs, args, label, flag = check_stacked("pop {r1,r0}", address_list, line_list, stacked_memory)
# print("Registers:", regs)
# print("Arguments:", args)
# print("Label:", label)
# print("Flag:", flag)
# print("Stacked Memory:", stacked_memory)
# print("SP after pop:", line_edit_dict["sp"].text())
# print()

# print("--- Testing POP {pc} ---")
# regs, args, label, flag = check_stacked("pop {pc}", address_list, line_list, stacked_memory)
# print("Registers:", regs)
# print("Arguments:", args)
# print("Label:", label)
# print("Flag:", flag)
# print("Stacked Memory:", stacked_memory)
# print("SP after pop pc:", line_edit_dict["sp"].text())
# print()

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
def MOV(temporary, line):
    if len(temporary) == 1:
        return temporary
    else:
        print(f"Error: Bad arguments to instruction '{line.strip()}'")
        return None
# print(MOV(["r0"], "MOV r0, #1"))  # should return ['r0']
# print(MOV(["r0", "#1"], "MOV r0, #1"))  # should return None with error message

def MVN(temporary, line):
    result = []
    if len(temporary) == 1:
        result.append(dict.complement(temporary[0]))
        return result
    else:
        print(f"Error: Bad arguments to instruction '{line.strip()}'")
        return None
# print(MVN(["r0"], "MVN r0"))  # should return ['~r0']
# print(MVN(["r0", "#1"], "MVN r0, #1"))  # should return None with error message

# LSR (Logical Shift Right) instruction implementation
def LSR_C(temporary, line):
    if len(temporary) < 2:
        carry = '0'
        return None, carry
    reg = temporary[0]
    shift_str = temporary[1]
    reg_value = line_edit_dict.get(reg)
    val_str = reg_value.text()
    val_bin = format(int(val_str, 16), '032b')  # convert hex to 32-bit binary
    shift_val = Decoder(shift_str)
    result, carry = dict.r_shift_32_c(val_bin, shift_val, line)
    return result, carry
# print(LSR_C(["r0", "2"], "LSR r0, #2"))  # should return (result, carry)

# LSL (Logical Shift Left) instruction implementation
def LSL_C(temporary, line):
    if len(temporary) < 2:
        carry = '0'
        return None, carry

    reg = temporary[0]
    shift_str = temporary[1]

    reg_value = line_edit_dict.get(reg)
    val_str = reg_value.text()
    try:
        val_bin = format(int(val_str, 16), '032b')
    except ValueError:
        print(f"Error: Invalid value in register {reg} for line '{line}'")
        return None, None

    shift_val = Decoder(shift_str)
    result, carry = dict.l_shift_32_c(val_bin, shift_val, line)
    return result, carry
# print(LSL_C(["r0", "2"], "LSL r0, #2"))  # should return (result, carry)

# ASR (Arithmetic Shift Right) instruction implementation
def ASR_C(temporary, line):
    if len(temporary) < 2:
        carry = '0'
        return None, carry

    reg = temporary[0]
    shift_str = temporary[1]

    reg_value = line_edit_dict.get(reg)

    val_str = reg_value.text()
    try:
        val_bin = format(int(val_str, 16), '032b')
    except ValueError:
        print(f"Error: Invalid value in register {reg} for line '{line}'")
        return None, None

    shift_val = Decoder(shift_str)
    result, carry = dict.asr_shift_32_c(val_bin, shift_val, line)
    return result, carry
# print(ASR_C(["r0", "2"], "ASR r0, #2"))  # should return (result, carry)

def ROR_C(temporary, line): pass
def RRX_C(temporary, line): pass
def AND(temporary, line): pass
def BIC(temporary, line): pass
def ORR(temporary, line): pass
def EOR(temporary, line): pass
def ADC(temporary, line): pass
def SBC(temporary, line): pass
def RSB(temporary, line): pass
def REV(temporary, line): pass
def RBIT(temporary, line): pass
def MLA(temporary, line): pass
def MLS(temporary, line): pass
def UMLA(temporary, line): pass
def UMLS(temporary, line): pass
def SMLA(temporary, line): pass
def SMLS(temporary, line): pass
def SAT(temporary, line): pass
def LDR(temporary, line): pass
def LDR_B(temporary, line): pass
def LDR_H(temporary, line): pass
def STR(temporary, line): pass
def STR_B(temporary, line): pass
def STR_H(temporary, line): pass

