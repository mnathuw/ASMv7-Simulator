# ASMv7-Simulator
A Python-based simulator and disassembler for the ARMv7 23-bit ISA and 16-bit Thumb intruction set. This project was developed as part of CP216 Intro to Microprocessors

## Features:
1. ARMv7 & Thumb Instruction Support
2. Instruction Decoding & Encoding
3. Pipelined CPU Modeling
4. Memory Model
5. Register State Management
6. Simulation Output
7. Extensible Lookup Tables
9. Test Cases
10. Optional GUI Interface

## Install and setup:
Install Python (3.8+ recommended)
2. Clone the repository:
```
git clone https://github.com/mnathuw/ASMv7-Simulator.git
cd ASMv7-Simulator
```
3. Run test program
```
python assembly.py Demo/find_max_thumb.txt
```
4. [Optional] Launch the GUI (if this task has done)
```
python ui.py
```

## Project structure:
ARMv7-simulator/
├── assembly.py # Main driver: loads, decodes, and executes instructions
├── memory.py # Memory model: read/write logic, memory setup
├── data.py # CPU state: general-purpose registers, flags, constants
├── decoder.py # Disassembler: converts binary to readable instructions
├── encoder.py # Assembler: converts instructions to binary format
├── dict.py # Lookup tables for opcodes, registers, flags, etc.
├── ui.py # (Optional) GUI to visualize instruction execution
├── demo/ # Sample test programs
│ ├── test1.txt # Example: ADD r1, r2, r3
│ ├── test2.txt # Example: MOV r0, #5
└── README.md # Project overview and usage guide

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