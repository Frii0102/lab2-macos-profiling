"""Синтетичні дані ТІЛЬКИ для тестів коду, не результати лабораторної."""
import unittest
from energy import parse_block, integrate
from summarize import parse


class AnalysisTests(unittest.TestCase):
    def test_power_units(self):
        block = '*** Sampled system activity (100ms elapsed) ***\nCPU Power: 2000 mW\nGPU Power: 0 mW\nANE Power: 0 mW\n'
        sample = parse_block(block, 10)
        self.assertAlmostEqual(sample['watts'], 2)
        self.assertAlmostEqual(sample['duration'], 0.1)
        self.assertAlmostEqual(sample['start'], 9.9)

    def test_missing_sensor_not_zero(self):
        self.assertIsNone(parse_block('(100ms elapsed)\nCPU Power: 10 mW\n', 10))

    def test_partial_overlap(self):
        energy, coverage, _ = integrate([dict(start=0, end=1, watts=2),
                                         dict(start=1, end=2, watts=4)], .5, 1.5)
        self.assertAlmostEqual(energy, 3)
        self.assertAlmostEqual(coverage, 1)

    def test_overlap_not_double_counted(self):
        energy, coverage, _ = integrate([dict(start=0, end=1, watts=2),
                                         dict(start=.9, end=2, watts=2)], 0, 2)
        self.assertAlmostEqual(energy, 4)
        self.assertAlmostEqual(coverage, 1)

    def test_missing_data_rejected(self):
        with self.assertRaises(ValueError):
            integrate([dict(start=0, end=1, watts=2)], 0, 2)

    def test_ipc(self):
        r = parse('1.0 real 0.9 user 0.1 sys\n 100 instructions retired\n 50 cycles elapsed\n',
                  'mode=fixed-work elements=10 repetitions=2 checksum=100 kernel_seconds=0.8 check=OK')
        self.assertEqual(r['ipc'], 2)
        self.assertIsNone(r['rss_bytes'])

    def test_fixed_duration_rejected(self):
        with self.assertRaises(ValueError):
            parse('', 'mode=fixed-duration-profile check=OK')


if __name__ == '__main__':
    unittest.main()
