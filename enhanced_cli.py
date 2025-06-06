#!/usr/bin/env python3
"""
Enhanced CLI wrapper for the Predictor portfolio management system.

This script serves as an entry point to the enhanced CLI, delegating to the
modular implementation in the enhanced_cli package.

This module re-exports the EnhancedCLI class from enhanced_cli.main to 
maintain compatibility with code that imports from here.
"""

# Re-export the EnhancedCLI class for backward compatibility
from enhanced_cli.main import EnhancedCLI, main

if __name__ == "__main__":
    main()
