# ARMv7-Simulator

A Python-based simulator and disassembler for the ARMv7 32-bit ISA and 16-bit Thumb instruction set. This project was developed as part of CP216 Intro to Microprocessors.

## Features

1. ARMv7 and Thumb instruction support
2. Instruction decoding and encoding
3. Pipelined CPU modeling
4. Memory model implementation
5. Register state management
6. Simulation output displaying register and memory changes
7. Extensible lookup tables for opcodes and registers
8. Test cases for verification
9. Optional GUI interface for visualization

## Installation and Setup

1. Clone the repository (Python 3.8+ recommended)
```bash
git clone https://github.com/mnathuw/ARMv7-Simulator.git
cd ARMv7-Simulator
```
2. Run test program
```bash
python assembly.py Demo/find_max_thumb.txt
```
3. [Optional] Launch the GUI (if this task has done)
```bash
python ui.py
```

## Project structure:
ARMv7-Simulator/
├── assembly.py       # Main driver: loads, decodes, and executes instructions
├── memory.py         # Memory model: read/write logic and memory setup
├── data.py           # CPU state: general-purpose registers, flags, constants
├── decoder.py        # Disassembler: binary to assembly translation
├── encoder.py        # Assembler: assembly to binary translation
├── dict.py           # Lookup tables for opcodes, registers, flags, etc.
├── ui.py             # (Optional) GUI to visualize instruction execution
├── demo/             # Sample test programs
│   ├── test1.txt     # Example: ADD r1, r2, r3
│   ├── test2.txt     # Example: MOV r0, #5
└── README.md         # Project overview and usage guide


## Collaborators:
[@AbiaShahbaz](https://github.com/AbiaShahbaz) [@mnathuw](https://github.com/mnathuw)

## To do:
✅ decoder.py
✅ encoder.py
✅ test1.txt
🚧 assembly.py
🚧 memory.py
❎ data.py
❎ dict.py

## License
This project is open-source under the **MIT License**.