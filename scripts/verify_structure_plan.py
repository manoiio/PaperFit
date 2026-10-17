"""Handwritten ordinary/numeric/section oracle; no classification or policy parser."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.verify_page_output import verify as raw_verify

def verify(source,formatted,final):
    return raw_verify(source,formatted,formatted,final,fresh=True,body_start=5)
