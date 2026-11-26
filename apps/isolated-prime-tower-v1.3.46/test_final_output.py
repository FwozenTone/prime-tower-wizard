import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import tower_wizard as wizard

class FinalOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'some project.3mf';self.source.write_bytes(b'original')
        self.work=self.root/'working';self.work.mkdir()
        self.w=wizard.Workflow();self.w.source=self.source;self.w.work_folder=self.work
        self.w.output=self.work/'some project_tower.3mf';self.w.output.write_bytes(b'generated')
        (self.work/'debug.log').write_text('log');Path(str(self.w.output)+'.ipt.json').write_text('{}')
        (self.work/'slice').mkdir();(self.work/'slice'/'test.gcode').write_text('gcode')
    def tearDown(self):self.temp.cleanup()
    def test_default_keeps_only_versioned_project_and_original(self):
        self.w.finish_output()
        self.assertEqual('some project_tower_v1.3mf',self.w.output.name)
        self.assertEqual(b'generated',self.w.output.read_bytes())
        self.assertEqual(b'original',self.source.read_bytes())
        self.assertEqual({self.source.name,self.w.output.name},{p.name for p in self.root.iterdir()})
        self.assertEqual(str(self.w.output),self.w.state['project'])
        self.w.finish_output() # Finishing twice must not create another version.
        self.assertEqual(2,len(list(self.root.iterdir())))
    def test_existing_versions_are_never_overwritten(self):
        for n in (1,2):(self.root/f'some project_tower_v{n}.3mf').write_bytes(b'existing')
        self.w.finish_output();self.assertEqual('some project_tower_v3.3mf',self.w.output.name)
        for n in (1,2):self.assertEqual(b'existing',(self.root/f'some project_tower_v{n}.3mf').read_bytes())
    def test_debug_option_keeps_work_but_publishes_only_3mf(self):
        self.w.keep_working=True;self.w.finish_output()
        self.assertTrue((self.work/'debug.log').exists())
        self.assertFalse(Path(str(self.w.output)+'.ipt.json').exists())
        self.assertEqual(self.root,self.w.output.parent)
    def test_copy_failure_preserves_work_and_removes_partial_destination(self):
        with patch.object(wizard.shutil,'copyfileobj',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.w.finish_output()
        self.assertTrue(self.work.exists());self.assertEqual(b'generated',self.w.output.read_bytes())
        self.assertFalse((self.root/'some project_tower_v1.3mf').exists())
    def test_working_location_does_not_change_final_destination(self):
        other=self.root/'alternate';other.mkdir();moved=other/'working';self.work.rename(moved)
        self.w.work_folder=moved;self.w.output=moved/self.w.output.name
        self.w.finish_output();self.assertEqual(self.root,self.w.output.parent);self.assertFalse(moved.exists())

if __name__=='__main__':unittest.main()
