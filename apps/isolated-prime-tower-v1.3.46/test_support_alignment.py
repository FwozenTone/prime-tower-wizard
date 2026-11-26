import json,zipfile,unittest
from unittest.mock import patch
import test_isolated_prime_tower as core
import isolated_prime_tower as ipt
import tower_wizard as wizard

class SupportAlignmentTests(unittest.TestCase):
 setUp=core.ProjectTests.setUp
 tearDown=core.ProjectTests.tearDown
 fixture=core.ProjectTests.fixture
 def test_reference_preserves_source_and_geometry_and_limits(self):
  source,files=self.fixture();s=json.loads(files[ipt.SETTINGS]);s['independent_support_layer_height']='1';s['min_layer_height']=['.08']*3
  files[ipt.SETTINGS]=json.dumps(s).encode()
  with zipfile.ZipFile(source,'w') as z:
   for n,data in files.items():z.writestr(n,data)
  original=source.read_bytes()
  for branch in ('mainline','snapmaker'):
   w=wizard.Workflow();w.slicer_branch=branch;w.output=self.folder/'tower.3mf'
   target=w.prepare_reference(source)
   with zipfile.ZipFile(target) as z:
    aligned=json.loads(z.read(ipt.SETTINGS));self.assertEqual('0',aligned['independent_support_layer_height'])
    self.assertIn('independent_support_layer_height',aligned['different_settings_to_system'][0].split(';'))
    self.assertEqual(s['min_layer_height'],aligned['min_layer_height'])
    for n,data in files.items():
     if n!=ipt.SETTINGS:self.assertEqual(data,z.read(n))
   self.assertEqual(original,source.read_bytes())
