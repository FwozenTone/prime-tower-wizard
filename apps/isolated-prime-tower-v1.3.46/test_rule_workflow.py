import unittest
from unittest.mock import patch
import test_multiplate as multi
import tower_wizard as wizard

class RuleWorkflowTests(unittest.TestCase):
 setUp=multi.MultiPlateTests.setUp
 tearDown=multi.MultiPlateTests.tearDown
 fixture=multi.MultiPlateTests.fixture
 project=multi.MultiPlateTests.project
 write=multi.MultiPlateTests.write
 reference=multi.MultiPlateTests.reference
 def one_tool_reference(self,plate):
  p=self.folder/f'one_{plate}.gcode';p.write_text('G90\nM83\nT0\nG0 X1 Y1\n;Z:.2\n;TYPE:Outer wall\nG1 X2 E1\n;Z:10\nG1 X3 E1');return p
 def test_only_selected_plates_report_skip_and_others_generate(self):
  source,_=self.project();original=source.read_bytes();w=wizard.Workflow();selected=[]
  def sliced(*args):
   selected.append(w.plate)
   return self.one_tool_reference(w.plate) if w.plate==1 else self.reference(w.plate)
  with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=sliced):
   w.automatic({'source':str(source),'plates':[1,3],'plate_options':{'3':{'frame_slot':4}},'open_after':False})
  self.assertEqual([1,3],selected);self.assertEqual([False,False,True],[p['has_tower'] for p in wizard.plates(w.output)])
  self.assertTrue(w.state['result']['plates'][0]['skipped']);self.assertNotIn('error',w.state['result']['plates'][0])
  log='\n'.join(w.state['events']);self.assertIn('Plate 1: No prime tower needed',log);self.assertNotIn('Plate 2:',log)
  self.assertEqual(original,source.read_bytes())
 def test_all_skipped_has_no_output_and_cleans_working_folder(self):
  source,_=self.project();w=wizard.Workflow()
  with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=lambda *a:self.one_tool_reference(w.plate)),patch.object(w,'open_project') as opened:
   w.automatic({'source':str(source),'plates':[1,3],'open_after':True})
  self.assertEqual('no_tower_needed',w.state['stage']);self.assertFalse(w.output.exists());self.assertIsNone(w.work_folder);opened.assert_not_called()
 def test_single_selected_skip_is_not_generation_failure(self):
  source,_=self.project();w=wizard.Workflow()
  with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',return_value=self.one_tool_reference(1)),patch.object(w,'open_project') as opened:
   w.automatic({'source':str(source),'plates':[1],'open_after':True})
  self.assertEqual('no_tower_needed',w.state['stage']);self.assertIsNone(w.work_folder);opened.assert_not_called()
 def test_missing_frame_selection_fails_only_that_plate(self):
  source,_=self.project();w=wizard.Workflow()
  with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=lambda *a:self.reference(w.plate)):
   w.automatic({'source':str(source),'plates':[1,3],'plate_options':{'3':{'frame_slot':3}},'open_after':False})
  rows=w.state['result']['plates'];self.assertIn('Select the prime tower outer wall',rows[0]['error']);self.assertTrue(rows[1]['generated'])
