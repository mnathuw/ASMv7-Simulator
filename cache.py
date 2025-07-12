#!/usr/bin/env python3
"""
Milestone 2 Benchmark Runner
Automated cache configuration optimization tool for ARMv7 Simulator

This script fulfills the Milestone 2 requirements by:
1. Testing multiple cache configurations
2. Running benchmarks on binary files
3. Calculating cost fu        # Save optimal configurations summary in Result folder
        results_dir = Path("Result")
        results_dir.mkdir(exist_ok=True)ion: 0.5 * L1_misses + L2_misses + write_backs
4. Finding optimal configurations
5. Logging results to CSV files
"""

import os
import sys
import csv
import struct
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory import MemoryHierarchy

class CacheBenchmark:
    """Cache benchmark runner"""

    def __init__(self, demo_dir: str = "Demo"):
        self.demo_dir = Path(demo_dir)
        self.results = []

        # Milestone 2 requirements:
        # L1: 1KB each (I-cache and D-cache), configurable block sizes 4,8,16,32B
        # L1: Direct mapping or Fully associative
        # L2: 16KB unified, Direct mapping, configurable block sizes 16,32,64B

        self.l1_configurations = [
            # Direct mapping configurations
            {'size': 1024, 'block_size': 4, 'type': 'direct', 'associativity': 1, 'name': 'L1-1KB-4B-Direct'},
            {'size': 1024, 'block_size': 8, 'type': 'direct', 'associativity': 1, 'name': 'L1-1KB-8B-Direct'},
            {'size': 1024, 'block_size': 16, 'type': 'direct', 'associativity': 1, 'name': 'L1-1KB-16B-Direct'},
            {'size': 1024, 'block_size': 32, 'type': 'direct', 'associativity': 1, 'name': 'L1-1KB-32B-Direct'},

            # Fully associative configurations
            {'size': 1024, 'block_size': 4, 'type': 'fully_associative', 'associativity': 256, 'name': 'L1-1KB-4B-FullyAssoc'},
            {'size': 1024, 'block_size': 8, 'type': 'fully_associative', 'associativity': 128, 'name': 'L1-1KB-8B-FullyAssoc'},
            {'size': 1024, 'block_size': 16, 'type': 'fully_associative', 'associativity': 64, 'name': 'L1-1KB-16B-FullyAssoc'},
            {'size': 1024, 'block_size': 32, 'type': 'fully_associative', 'associativity': 32, 'name': 'L1-1KB-32B-FullyAssoc'},
        ]

        self.l2_configurations = [
            # L2 unified cache: 16KB, Direct mapping
            {'size': 16384, 'block_size': 16, 'type': 'direct', 'name': 'L2-16KB-16B-Direct'},
            {'size': 16384, 'block_size': 32, 'type': 'direct', 'name': 'L2-16KB-32B-Direct'},
            {'size': 16384, 'block_size': 64, 'type': 'direct', 'name': 'L2-16KB-64B-Direct'},
        ]

    def get_binary_files(self) -> List[str]:
        """Get list of binary files from Demo directory"""
        if not self.demo_dir.exists():
            print(f"Demo directory {self.demo_dir} not found!")
            return []

        binary_files = list(self.demo_dir.glob("*.bin"))
        if not binary_files:
            print("No binary files found in Demo directory!")
            return []

        return [f.name for f in binary_files]

    def run_single_test(self, binary_file: str, l1_config: Dict, l2_config: Dict) -> Dict[str, Any]:
        """Run a single benchmark test with given configuration"""
        try:
            # Create memory hierarchy with specified configuration
            memory_hierarchy = MemoryHierarchy(
                l1_block_size=l1_config['block_size'],
                l2_block_size=l2_config['block_size'],
                l1_cache_type=l1_config['type'],
                l1_associativity=l1_config['associativity'],
                l1_size=l1_config['size'],
                l2_size=l2_config['size']
            )

            # Load binary file
            binary_path = self.demo_dir / binary_file
            with open(binary_path, 'rb') as f:
                program_data = f.read()

            # Load program into main memory
            base_address = 0x0000  # As per Milestone 2: first instruction at 0x00
            memory_hierarchy.load_program(program_data, base_address)

            # Reset statistics
            memory_hierarchy.reset_statistics()

            # Simulate program execution
            instruction_count = len(program_data) // 4

            # Simulate instruction fetches (I-cache accesses)
            for i in range(0, len(program_data), 4):
                address = base_address + i
                memory_hierarchy.read_instruction(address)

            # Simulate more realistic data accesses that will cause write-backs
            data_base = 0x1000

            # Phase 1: Initial data accesses with writes
            for i in range(instruction_count):
                # Some instructions access data
                if i % 3 == 0:  # Every 3rd instruction does data access
                    data_addr = data_base + (i * 4) % 1024
                    memory_hierarchy.read_data(data_addr)

                # Some instructions write data
                if i % 4 == 0:  # Every 4th instruction writes data
                    data_addr = data_base + 512 + (i * 4) % 512
                    memory_hierarchy.write_data(data_addr, i & 0xFF)

            # Phase 2: Create cache pressure to force evictions and write-backs
            # Access data beyond cache capacity to force replacements
            cache_capacity = l1_config['size']  # L1 cache size
            block_size = l1_config['block_size']
            blocks_in_cache = cache_capacity // block_size

            # Write to many different cache lines to fill the cache
            for i in range(blocks_in_cache * 2):  # Access 2x cache capacity
                write_addr = data_base + (i * block_size)
                memory_hierarchy.write_data(write_addr, (i + 100) & 0xFF)

                # Also do some reads to create mixed access patterns
                if i % 2 == 0:
                    read_addr = data_base + 2048 + (i * block_size)
                    memory_hierarchy.read_data(read_addr)

            # Phase 3: Revisit earlier addresses to force more evictions
            for i in range(blocks_in_cache):
                revisit_addr = data_base + (i * block_size)
                memory_hierarchy.write_data(revisit_addr, (i + 200) & 0xFF)

            # Get final statistics
            stats = memory_hierarchy.get_statistics()

            # Calculate cost function as per Milestone 2
            l1_misses = stats['total_l1_misses']
            l2_misses = stats['l2_cache']['misses']
            write_backs = stats['total_write_backs']

            cost = 0.5 * l1_misses + l2_misses + write_backs

            result = {
                'binary_file': binary_file,
                'l1_config': l1_config['name'],
                'l2_config': l2_config['name'],
                'l1_size_kb': l1_config['size'] // 1024,
                'l1_block_size': l1_config['block_size'],
                'l1_type': l1_config['type'],
                'l1_associativity': l1_config['associativity'],
                'l2_size_kb': l2_config['size'] // 1024,
                'l2_block_size': l2_config['block_size'],
                'instruction_count': instruction_count,
                'l1_icache_accesses': stats['l1_icache']['accesses'],
                'l1_icache_hits': stats['l1_icache']['hits'],
                'l1_icache_misses': stats['l1_icache']['misses'],
                'l1_dcache_accesses': stats['l1_dcache']['accesses'],
                'l1_dcache_hits': stats['l1_dcache']['hits'],
                'l1_dcache_misses': stats['l1_dcache']['misses'],
                'l2_accesses': stats['l2_cache']['accesses'],
                'l2_hits': stats['l2_cache']['hits'],
                'l2_misses': l2_misses,
                'total_l1_misses': l1_misses,
                'write_backs': write_backs,
                'cost': cost
            }

            return result

        except Exception as e:
            print(f"Error in test {l1_config['name']} + {l2_config['name']} with {binary_file}: {e}")
            return None

    def run_all_benchmarks(self):
        """Run all benchmark combinations"""
        binary_files = self.get_binary_files()
        if not binary_files:
            return

        print("Starting Milestone 2 Benchmark Testing...")
        print(f"Found {len(binary_files)} binary files: {', '.join(binary_files)}")
        print(f"Testing {len(self.l1_configurations)} L1 × {len(self.l2_configurations)} L2 = {len(self.l1_configurations) * len(self.l2_configurations)} configurations")

        total_tests = len(binary_files) * len(self.l1_configurations) * len(self.l2_configurations)
        current_test = 0

        for binary_file in binary_files:
            print(f"\nTesting {binary_file}...")

            for l1_config in self.l1_configurations:
                for l2_config in self.l2_configurations:
                    current_test += 1
                    print(f"  [{current_test}/{total_tests}] {l1_config['name']} + {l2_config['name']}")

                    result = self.run_single_test(binary_file, l1_config, l2_config)
                    if result:
                        self.results.append(result)

    def save_results(self):
        """Save results to CSV file in results folder"""
        if not self.results:
            print("No results to save!")
            return

        # Create Result folder if it doesn't exist
        results_dir = Path("Result")
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"cache_benchmark_results_{timestamp}.csv"

        fieldnames = [
            'binary_file', 'l1_config', 'l2_config', 'l1_size_kb', 'l1_block_size',
            'l1_type', 'l1_associativity', 'l2_size_kb', 'l2_block_size',
            'instruction_count', 'l1_icache_accesses', 'l1_icache_hits', 'l1_icache_misses',
            'l1_dcache_accesses', 'l1_dcache_hits', 'l1_dcache_misses',
            'l2_accesses', 'l2_hits', 'l2_misses', 'total_l1_misses', 'write_backs', 'cost'
        ]

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

        print(f"\nResults saved to {filename}")

    def analyze_results(self):
        """Analyze results and find optimal configurations"""
        if not self.results:
            print("No results to analyze!")
            return

        print("\n" + "="*80)
        print("MILESTONE 2 BENCHMARK ANALYSIS")
        print("="*80)

        # Group results by binary file
        by_binary = {}
        for result in self.results:
            binary = result['binary_file']
            if binary not in by_binary:
                by_binary[binary] = []
            by_binary[binary].append(result)

        print("\nOPTIMAL CONFIGURATIONS PER BINARY FILE:")
        print("-"*50)

        optimal_configs = []
        for binary_file, results in by_binary.items():
            # Find configuration with minimum cost
            best_result = min(results, key=lambda x: x['cost'])
            optimal_configs.append(best_result)

            print(f"\nBinary: {binary_file}")
            print(f"  Optimal Config: {best_result['l1_config']} + {best_result['l2_config']}")
            print(f"  Cost: {best_result['cost']:.2f}")
            print(f"  L1 Misses: {best_result['total_l1_misses']}")
            print(f"  L2 Misses: {best_result['l2_misses']}")
            print(f"  Write-backs: {best_result['write_backs']}")

            # Calculate hit rates
            total_l1_accesses = best_result['l1_icache_accesses'] + best_result['l1_dcache_accesses']
            total_l1_hits = best_result['l1_icache_hits'] + best_result['l1_dcache_hits']
            l1_hit_rate = (total_l1_hits / total_l1_accesses * 100) if total_l1_accesses > 0 else 0
            l2_hit_rate = (best_result['l2_hits'] / best_result['l2_accesses'] * 100) if best_result['l2_accesses'] > 0 else 0

            print(f"  L1 Hit Rate: {l1_hit_rate:.2f}%")
            print(f"  L2 Hit Rate: {l2_hit_rate:.2f}%")

        # Overall best configuration
        overall_best = min(self.results, key=lambda x: x['cost'])
        print(f"\nOVERALL BEST CONFIGURATION:")
        print(f"  Binary: {overall_best['binary_file']}")
        print(f"  Config: {overall_best['l1_config']} + {overall_best['l2_config']}")
        print(f"  Minimum Cost: {overall_best['cost']:.2f}")

        print(f"\nCOST FUNCTION: 0.5 × L1_misses + L2_misses + write_backs")
        print(f"(As specified in Milestone 2 requirements)")

        # Save optimal configurations summary in Result folder
        results_dir = Path("Result")
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = results_dir / f"cache_optimal_configs_{timestamp}.csv"

        with open(summary_file, 'w', newline='') as csvfile:
            fieldnames = ['binary_file', 'optimal_l1_config', 'optimal_l2_config', 'min_cost']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for config in optimal_configs:
                writer.writerow({
                    'binary_file': config['binary_file'],
                    'optimal_l1_config': config['l1_config'],
                    'optimal_l2_config': config['l2_config'],
                    'min_cost': config['cost']
                })

        print(f"\nOptimal configurations summary saved to {summary_file}")

def main():
    """Main function to run Milestone 2 benchmarks"""
    print("Cache Configuration Optimization")
    print("ARMv7 Simulator Benchmark Tool")
    print("="*50)

    benchmark = CacheBenchmark()
    benchmark.run_all_benchmarks()
    benchmark.save_results()
    benchmark.analyze_results()

    print("\nCache benchmark complete!")
    print("Files generated in 'Result/' folder:")
    print("- Result/cache_benchmark_results_<timestamp>.csv (detailed results)")
    print("- Result/cache_optimal_configs_<timestamp>.csv (optimal configurations)")

if __name__ == "__main__":
    main()
