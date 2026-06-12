import unittest
import coverage
import sys
import os

def main():
    # Start coverage
    cov = coverage.Coverage()
    cov.start()

    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Stop and save coverage
    cov.stop()
    cov.save()

    # Print test summary report
    print("\n" + "="*70)
    print("TEST SUMMARY REPORT")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Skipped: {len(result.skipped)}")
    print("="*70)

    # Return appropriate exit code
    if not result.wasSuccessful():
        sys.exit(1)
    else:
        # Enforce greater than 80% coverage
        print("\nCOVERAGE REPORT")
        print("="*70)
        coverage_percentage = cov.report()
        if coverage_percentage < 80.0:
             print(f"\nCoverage is {coverage_percentage:.2f}%, which is below the required 80.0%.")
             sys.exit(1)
        sys.exit(0)

if __name__ == '__main__':
    main()
