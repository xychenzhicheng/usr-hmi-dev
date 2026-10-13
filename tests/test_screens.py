#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for full screen synthesis and SVG wireframe generation."""

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hmi_widget_builder as builder
from hmi_svg_preview import generate_screen_svg


class TestScreenSynthesis(unittest.TestCase):
    def test_build_screen(self):
        w1 = builder.build_label(10, 10, 200, 50, "标题", idx=0)
        w2 = builder.build_numeric_1dec(10, 70, 150, 50, 300, idx=1)
        s_bin = builder.build_screen("004", "AprilTag饲喂设置", [w1, w2], bg_rgb=(244, 246, 249))
        self.assertIsInstance(s_bin, bytes)
        # Verify 1024x600 in screen preheader
        width, height = struct.unpack(">dd", s_bin[16:32])
        self.assertEqual(width, 1024.0)
        self.assertEqual(height, 600.0)
        # Verify screen name in UTF-16BE
        self.assertIn("AprilTag饲喂设置".encode("utf-16-be"), s_bin)
        self.assertIn("004".encode("utf-16-be"), s_bin)

    def test_generate_screen_svg(self):
        spec = {
            "screen_no": "001",
            "screen_name": "测试预览",
            "widgets": [
                {"type": "label", "x": 10, "y": 10, "w": 300, "h": 50, "text": "测试标题"},
                {"type": "numeric_1dec", "x": 10, "y": 80, "w": 150, "h": 50, "reg_num": 300, "name": "前左"},
                {"type": "jump_button", "x": 200, "y": 80, "w": 150, "h": 50, "label": "返回", "target_screen": "000:画面1"},
            ],
        }
        svg_str = generate_screen_svg(spec)
        self.assertIn("<svg", svg_str)
        self.assertIn("</svg>", svg_str)
        self.assertIn("测试标题", svg_str)
        self.assertIn("[4x300]", svg_str)
        self.assertIn("-&gt; 000:画面1", svg_str)


if __name__ == "__main__":
    unittest.main()
