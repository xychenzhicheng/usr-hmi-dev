#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for industrial semantic and layout validation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from hmi_validator import validate_screen_spec


class TestValidator(unittest.TestCase):
    def test_valid_spec(self):
        spec = {
            "screen_no": "001",
            "screen_name": "正常画面",
            "widgets": [
                {"type": "label", "x": 10, "y": 10, "w": 300, "h": 50, "text": "饲喂设定 (kg)"},
                {"type": "numeric_1dec", "x": 10, "y": 80, "w": 150, "h": 50, "reg_num": 300},
                {"type": "numeric_1dec", "x": 180, "y": 80, "w": 150, "h": 50, "reg_num": 301},
            ],
        }
        is_valid, errors, warnings = validate_screen_spec(spec)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)

    def test_out_of_bounds_error(self):
        spec = {
            "screen_no": "001",
            "screen_name": "越界画面",
            "widgets": [
                {"type": "label", "x": 900, "y": 10, "w": 200, "h": 50, "text": "超出了1024宽度"},
            ],
        }
        is_valid, errors, warnings = validate_screen_spec(spec)
        self.assertFalse(is_valid)
        self.assertTrue(any("bounds" in e.lower() for e in errors))

    def test_unit_mismatch_warning(self):
        spec = {
            "screen_no": "001",
            "screen_name": "单位混用",
            "widgets": [
                {"type": "label", "x": 10, "y": 10, "w": 300, "h": 50, "text": "喂多少斤"},
                {"type": "label", "x": 10, "y": 70, "w": 300, "h": 50, "text": "本趟总重 (kg)"},
            ],
        }
        is_valid, errors, warnings = validate_screen_spec(spec)
        self.assertTrue(is_valid)
        self.assertTrue(any("unit" in w.lower() for w in warnings))

    def test_duplicate_register_conflict(self):
        spec = {
            "screen_no": "001",
            "screen_name": "寄存器冲突",
            "widgets": [
                {"type": "numeric_1dec", "x": 10, "y": 10, "w": 150, "h": 50, "reg_num": 300, "editable": True},
                {"type": "numeric_1dec", "x": 180, "y": 10, "w": 150, "h": 50, "reg_num": 300, "editable": True},
            ],
        }
        is_valid, errors, warnings = validate_screen_spec(spec)
        self.assertTrue(is_valid)
        self.assertTrue(any("conflict" in w.lower() or "duplicate" in w.lower() for w in warnings))


if __name__ == "__main__":
    unittest.main()
