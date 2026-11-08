"""Entry point: python3 src/run.py server|relay|consumer"""
import sys

from bootstrap.wiring import main

main(sys.argv[1] if len(sys.argv) > 1 else "server")
