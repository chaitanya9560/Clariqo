"""Compatibility entry point for isolated verification (no live calls on import)."""
import unittest

def main():
    suite = unittest.defaultTestLoader.loadTestsFromName('test_working_flows')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    raise SystemExit(main())
