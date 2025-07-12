import struct
from enum import Enum
from typing import Dict, Tuple, Optional

# convert the binary string to a decimal integer
def Decoder(binary_str):
    if binary_str is None:
        raise ValueError("Decoder received None instead of binary string")

    # Handle case where input is a list (common issue with shift functions)
    if isinstance(binary_str, list):
        if len(binary_str) == 0:
            raise ValueError("Decoder received empty list")
        if len(binary_str) == 1:
            binary_str = binary_str[0]  # Extract the string from single-element list
        else:
            raise ValueError(f"Decoder received list with {len(binary_str)} elements, expected single string")

    if not isinstance(binary_str, str):
        raise TypeError(f"Decoder expected string, got {type(binary_str).__name__}: {binary_str}")
    if not binary_str:
        raise ValueError("Decoder received empty string")

    decimal = int(binary_str, 2)
    return decimal
# print(Decoder('00000000000000000000000000001010'))  # example usage, should print 10

class InstructionType(Enum):
    """ARM instruction types"""
    DATA_PROCESSING = "data_processing"
    MULTIPLY = "multiply"
    LOAD_STORE = "load_store"
    BRANCH = "branch"
    COPROCESSOR = "coprocessor"
    SOFTWARE_INTERRUPT = "swi"
    UNDEFINED = "undefined"

class ConditionCode(Enum):
    """ARM condition codes"""
    EQ = 0b0000  # Equal
    NE = 0b0001  # Not equal
    CS = 0b0010  # Carry set
    CC = 0b0011  # Carry clear
    MI = 0b0100  # Minus/negative
    PL = 0b0101  # Plus/positive or zero
    VS = 0b0110  # Overflow
    VC = 0b0111  # No overflow
    HI = 0b1000  # Unsigned higher
    LS = 0b1001  # Unsigned lower or same
    GE = 0b1010  # Signed greater than or equal
    LT = 0b1011  # Signed less than
    GT = 0b1100  # Signed greater than
    LE = 0b1101  # Signed less than or equal
    AL = 0b1110  # Always (unconditional)
    NV = 0b1111  # Never (deprecated)

class DataProcessingOpcode(Enum):
    """Data processing opcodes"""
    AND = 0b0000
    EOR = 0b0001
    SUB = 0b0010
    RSB = 0b0011
    ADD = 0b0100
    ADC = 0b0101
    SBC = 0b0110
    RSC = 0b0111
    TST = 0b1000
    TEQ = 0b1001
    CMP = 0b1010
    CMN = 0b1011
    ORR = 0b1100
    MOV = 0b1101
    BIC = 0b1110
    MVN = 0b1111

class ARMInstruction:
    """Represents a decoded ARM instruction"""

    def __init__(self, raw_instruction: int, pc: int):
        self.raw = raw_instruction
        self.pc = pc
        self.condition = ConditionCode((raw_instruction >> 28) & 0xF)
        self.instruction_type = self._decode_instruction_type()
        self.fields = self._decode_fields()

    def _decode_instruction_type(self) -> InstructionType:
        """Determine the instruction type from the raw instruction"""
        # Extract bits 27-25
        type_bits = (self.raw >> 25) & 0x7

        if type_bits == 0b000:
            # Check for multiply or data processing
            # Multiply: bits 7-4 = 1001
            if (self.raw >> 4) & 0xF == 0b1001:
                return InstructionType.MULTIPLY
            else:
                return InstructionType.DATA_PROCESSING
        elif type_bits == 0b001:
            return InstructionType.DATA_PROCESSING
        elif type_bits in [0b010, 0b011]:
            return InstructionType.LOAD_STORE
        elif type_bits == 0b100:
            return InstructionType.LOAD_STORE  # LDM/STM
        elif type_bits == 0b101:
            return InstructionType.BRANCH
        elif type_bits == 0b110:
            return InstructionType.COPROCESSOR
        elif type_bits == 0b111:
            if (self.raw >> 24) & 0x1:
                return InstructionType.SOFTWARE_INTERRUPT
            else:
                return InstructionType.COPROCESSOR
        else:
            return InstructionType.UNDEFINED

    def _decode_fields(self) -> Dict:
        """Decode instruction fields based on type"""
        if self.instruction_type == InstructionType.DATA_PROCESSING:
            return self._decode_data_processing()
        elif self.instruction_type == InstructionType.LOAD_STORE:
            return self._decode_load_store()
        elif self.instruction_type == InstructionType.BRANCH:
            return self._decode_branch()
        elif self.instruction_type == InstructionType.MULTIPLY:
            return self._decode_multiply()
        else:
            return {}

    def _decode_data_processing(self) -> Dict:
        """Decode data processing instruction"""
        immediate = (self.raw >> 25) & 0x1
        opcode = DataProcessingOpcode((self.raw >> 21) & 0xF)
        set_flags = (self.raw >> 20) & 0x1
        rn = (self.raw >> 16) & 0xF
        rd = (self.raw >> 12) & 0xF

        if immediate:
            # Immediate operand
            rotate = (self.raw >> 8) & 0xF
            imm = self.raw & 0xFF
            operand2 = self._rotate_right(imm, rotate * 2)
            operand2_reg = None
        else:
            # Register operand
            rm = self.raw & 0xF
            shift_type = (self.raw >> 5) & 0x3
            shift_by_reg = (self.raw >> 4) & 0x1

            if shift_by_reg:
                shift_reg = (self.raw >> 8) & 0xF
                shift_amount = None
            else:
                shift_amount = (self.raw >> 7) & 0x1F
                shift_reg = None

            operand2_reg = rm
            operand2 = {
                'register': rm,
                'shift_type': shift_type,
                'shift_amount': shift_amount,
                'shift_register': shift_reg
            }

        return {
            'opcode': opcode,
            'immediate': immediate,
            'set_flags': set_flags,
            'rn': rn,
            'rd': rd,
            'operand2': operand2,
            'operand2_reg': operand2_reg
        }

    def _decode_load_store(self) -> Dict:
        """Decode load/store instruction"""
        immediate = not ((self.raw >> 25) & 0x1)  # I bit: 0=immediate, 1=register
        pre_indexed = (self.raw >> 24) & 0x1
        up_down = (self.raw >> 23) & 0x1
        byte_word = (self.raw >> 22) & 0x1
        write_back = (self.raw >> 21) & 0x1
        load_store = (self.raw >> 20) & 0x1
        rn = (self.raw >> 16) & 0xF
        rd = (self.raw >> 12) & 0xF

        if immediate:
            offset = self.raw & 0xFFF
        else:
            rm = self.raw & 0xF
            shift_type = (self.raw >> 5) & 0x3
            shift_amount = (self.raw >> 7) & 0x1F
            offset = {
                'register': rm,
                'shift_type': shift_type,
                'shift_amount': shift_amount
            }

        return {
            'immediate': immediate,
            'pre_indexed': pre_indexed,
            'up_down': up_down,
            'byte_word': byte_word,
            'write_back': write_back,
            'load_store': load_store,
            'rn': rn,
            'rd': rd,
            'offset': offset
        }

    def _decode_branch(self) -> Dict:
        """Decode branch instruction"""
        link = (self.raw >> 24) & 0x1
        offset = self.raw & 0xFFFFFF

        # Sign extend 24-bit offset to 32-bit
        if offset & 0x800000:
            offset |= 0xFF000000

        # Convert to signed integer
        offset = struct.unpack('>i', struct.pack('>I', offset))[0]

        return {
            'link': link,
            'offset': offset,
            'target_address': self.pc + 8 + (offset << 2)
        }

    def _decode_multiply(self) -> Dict:
        """Decode multiply instruction"""
        accumulate = (self.raw >> 21) & 0x1
        set_flags = (self.raw >> 20) & 0x1
        rd = (self.raw >> 16) & 0xF
        rn = (self.raw >> 12) & 0xF
        rs = (self.raw >> 8) & 0xF
        rm = self.raw & 0xF

        return {
            'accumulate': accumulate,
            'set_flags': set_flags,
            'rd': rd,
            'rn': rn,
            'rs': rs,
            'rm': rm
        }

    def _rotate_right(self, value: int, amount: int) -> int:
        """Rotate value right by amount bits"""
        amount = amount % 32
        return ((value >> amount) | (value << (32 - amount))) & 0xFFFFFFFF

    def is_memory_access(self) -> bool:
        """Check if instruction accesses memory"""
        return self.instruction_type == InstructionType.LOAD_STORE

    def is_branch(self) -> bool:
        """Check if instruction is a branch"""
        return self.instruction_type == InstructionType.BRANCH

    def get_memory_address(self, registers: Dict[int, int]) -> Optional[int]:
        """Calculate memory address for load/store instructions"""
        if not self.is_memory_access():
            return None

        fields = self.fields
        base_addr = registers.get(fields['rn'], 0)

        if fields['immediate']:
            offset = fields['offset']
        else:
            # Register offset with optional shift
            offset_info = fields['offset']
            offset = registers.get(offset_info['register'], 0)

            # Apply shift if needed
            shift_type = offset_info.get('shift_type', 0)
            shift_amount = offset_info.get('shift_amount', 0)

            if shift_amount > 0:
                if shift_type == 0:  # LSL (Logical Shift Left)
                    offset = (offset << shift_amount) & 0xFFFFFFFF
                elif shift_type == 1:  # LSR (Logical Shift Right)
                    offset = offset >> shift_amount
                elif shift_type == 2:  # ASR (Arithmetic Shift Right)
                    if offset & 0x80000000:  # Sign bit set
                        offset = (offset >> shift_amount) | (0xFFFFFFFF << (32 - shift_amount))
                    else:
                        offset = offset >> shift_amount
                elif shift_type == 3:  # ROR (Rotate Right)
                    offset = self._rotate_right(offset, shift_amount)

        if fields['up_down']:
            return base_addr + offset
        else:
            return base_addr - offset

    def __str__(self) -> str:
        """String representation of the instruction"""
        return f"ARM Instruction: {self.instruction_type.value} at PC=0x{self.pc:08X}"

class InstructionDecoder:
    """ARM instruction decoder"""

    def __init__(self):
        self.instruction_count = 0

    def decode(self, raw_instruction: int, pc: int) -> ARMInstruction:
        """Decode a 32-bit ARM instruction"""
        self.instruction_count += 1
        return ARMInstruction(raw_instruction, pc)

    def decode_from_bytes(self, instruction_bytes: bytes, pc: int) -> ARMInstruction:
        """Decode instruction from 4 bytes (little-endian)"""
        if len(instruction_bytes) != 4:
            raise ValueError("ARM instructions must be exactly 4 bytes")

        # Unpack as little-endian 32-bit unsigned integer
        raw_instruction = struct.unpack('<I', instruction_bytes)[0]
        return self.decode(raw_instruction, pc)