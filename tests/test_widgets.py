#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for QDataStream binary widget synthesis."""

import struct
import sys
import unittest
from pathlib import Path

# Add scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hmi_widget_builder as builder


class TestWidgetBuilders(unittest.TestCase):
    def test_build_label(self):
        b = builder.build_label(10, 20, 200, 50, "猪舍标题", font_size=28, idx=0, z_val=1001.0)
        self.assertIsInstance(b, bytes)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x1C)
        z = struct.unpack(">d", b[-8:])[0]
        self.assertEqual(z, 1001.0)
        # Check text in UTF-16BE
        self.assertIn("猪舍标题".encode("utf-16-be"), b)

    def test_build_numeric_1dec(self):
        b = builder.build_numeric_1dec(50, 60, 160, 54, reg_num=300, name_str="前左槽", idx=1, z_val=1002.0)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x3F)
        self.assertIn("[Modbus_RTU_COM1_1]4x300".encode("utf-16-be"), b)
        self.assertIn("88888.8".encode("utf-16-be"), b)

    def test_build_numeric_int(self):
        b = builder.build_numeric_int(50, 60, 160, 54, reg_num=160, name_str="栏位号", idx=2, z_val=1003.0)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x3F)
        self.assertIn("[Modbus_RTU_COM1_1]4x160".encode("utf-16-be"), b)
        self.assertIn("88".encode("utf-16-be"), b)

    def test_build_write_button(self):
        b = builder.build_write_button(100, 200, 150, 60, "保存配置", reg_num=100, write_val=10, idx=3, z_val=1004.0)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x26)
        self.assertIn("[Modbus_RTU_COM1_1]4x100".encode("utf-16-be"), b)
        self.assertIn("10".encode("utf-16-be"), b)
        self.assertIn("保存配置".encode("utf-16-be"), b)

    def test_build_bit_button(self):
        b = builder.build_bit_button(100, 200, 150, 60, "开始配料", bit_addr="163.0", idx=4, z_val=1005.0)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x38)
        self.assertIn("[Modbus_RTU_COM1_1]4x_bit163.0".encode("utf-16-be"), b)
        self.assertIn("开始配料".encode("utf-16-be"), b)

    def test_build_jump_button(self):
        b = builder.build_jump_button(800, 20, 160, 60, "返回主页", target_screen="000:画面1", target_screen_list_idx=0, idx=5, z_val=1006.0)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x39)
        self.assertIn("000:画面1".encode("utf-16-be"), b)
        self.assertIn("返回主页".encode("utf-16-be"), b)

    def test_build_bit_lamp(self):
        b = builder.build_bit_lamp(200, 300, 165, 80, state0_text="水未到位", state1_text="水已到位", bit_addr="172.0", idx=6, z_val=1007.0)
        self.assertEqual(b[0], 1)
        wtype = struct.unpack(">I", b[1:5])[0]
        self.assertEqual(wtype, 0x51)
        self.assertIn("[Modbus_RTU_COM1_1]4x_bit172.0".encode("utf-16-be"), b)
        self.assertIn("水未到位".encode("utf-16-be"), b)
        self.assertIn("水已到位".encode("utf-16-be"), b)


if __name__ == "__main__":
    unittest.main()
