"""CLI readiness check; avoids inline Python quoting through Windows shells."""
from engine import load_catalog

if __name__ == '__main__':
    load_catalog()
    print('Approved career records ready')
