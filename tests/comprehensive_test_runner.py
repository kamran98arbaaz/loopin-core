#!/usr/bin/env python3
"""
Comprehensive test runner for all tests
"""
import unittest
import sys
import time
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_tests():
    """Run all tests and generate report"""
    # Record start time
    start_time = time.time()
    start_datetime = datetime.now()

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')

    # Create results directory
    results_dir = Path('test_results')
    results_dir.mkdir(exist_ok=True)

    # Create test result file
    result_file = results_dir / f'test_results_{start_datetime.strftime("%Y%m%d_%H%M%S")}.txt'
    
    with open(result_file, 'w') as f:
        # Write header
        f.write(f"Test Run: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # Run tests
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)

        # Calculate duration
        duration = time.time() - start_time

        # Write summary
        f.write("\n" + "=" * 80 + "\n")
        f.write("Test Summary:\n")
        f.write(f"Run Duration: {duration:.2f} seconds\n")
        f.write(f"Tests Run: {result.testsRun}\n")
        f.write(f"Failures: {len(result.failures)}\n")
        f.write(f"Errors: {len(result.errors)}\n")
        f.write(f"Skipped: {len(result.skipped)}\n")
        
        # Write failures and errors in detail
        if result.failures:
            f.write("\nFailures:\n")
            for failure in result.failures:
                f.write(f"\n{failure[0]}\n")
                f.write(f"{failure[1]}\n")
        
        if result.errors:
            f.write("\nErrors:\n")
            for error in result.errors:
                f.write(f"\n{error[0]}\n")
                f.write(f"{error[1]}\n")

    # Log results
    logger.info(f"Test run completed in {duration:.2f} seconds")
    logger.info(f"Results written to {result_file}")
    
    # Return success status
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
