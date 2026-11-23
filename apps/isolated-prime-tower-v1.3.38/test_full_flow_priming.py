import math
import unittest
from test_isolated_prime_tower import AuditTests

class FullFlowPrimingTests(unittest.TestCase):
 tearDown=AuditTests.tearDown
 check_code=AuditTests.check_code
 def setUp(self):
  AuditTests.setUp(self)
  self.manifest.update(priming_path_checks=True,tower_height=2.,purge_volume=.1)
 def sample(self):
  e=(.45*.2-(1-math.pi/4)*.2**2)*18/(math.pi*1.75**2/4)
  return 'G90\nM83\n;Z:2\n;WIDTH:.45\n;HEIGHT:.2\nG0 Z2\n'+''.join(f'T{tool}\nG0 X2 Y{y}\nG1 X20 Y{y} E{e:.8f}\nG0 X100 Y100\nG1 X110 E1\n' for tool,y in ((0,2),(1,6)))
 def test_normal_start(self):
  r=self.check_code(self.sample());self.assertTrue(r['passed'],r)
 def test_taper_rejected(self):
  s=self.sample();s=s.replace(s.split('G1 X20 Y2 E')[1].split('\n')[0],'.001',1)
  self.assertTrue(any('normal flow' in e for e in self.check_code(s)['errors']))
 def test_scarf_rejected(self):
  self.assertTrue(any('scarf' in e for e in self.check_code(self.sample().replace('G1 X20 Y2','G1 Z1.9 X20 Y2'))['errors']))
 def test_retrace_rejected(self):
  s=self.sample().replace('G0 X100 Y100','G1 X2 Y2 E.2\nG1 X20 Y2 E.2\nG0 X100 Y100',1)
  r=self.check_code(s)
  self.assertTrue(any('Repeated extrusion' in e for e in r['errors']))
  self.assertTrue(any('reversal' in e for e in r['errors']))
