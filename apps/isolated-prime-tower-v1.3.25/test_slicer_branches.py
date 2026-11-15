import json,plistlib,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import tower_wizard as wizard
import isolated_prime_tower as ipt
import test_isolated_prime_tower as core

class SlicerBranchTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def app(self,name,executable,version):
        app=self.root/name;binary=app/'Contents/MacOS'/executable;binary.parent.mkdir(parents=True);binary.write_text('#!/bin/sh\n');binary.chmod(0o755)
        (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':executable,'CFBundleShortVersionString':version}))
        return app
    def test_locations_are_independent_and_snapmaker_version_checked(self):
        main=self.app('OrcaSlicer.app','OrcaSlicer','2.5.1');snap=self.app('Snapmaker Orca.app','Snapmaker_Orca','2.4.1')
        with patch.object(wizard,'settings_file',return_value=self.root/'settings.json'):
            wizard.save_orca(main,'mainline');wizard.save_orca(snap,'snapmaker');choices=wizard.slicer_choices()
            self.assertEqual('2.5.1',choices['mainline']['version']);self.assertEqual('2.4.1',choices['snapmaker']['version'])
            self.assertEqual('snapmaker',wizard.load_settings()['slicer_branch'])
            with self.assertRaisesRegex(ipt.TowerError,'does not match'):wizard.save_orca(main,'snapmaker')
            old=self.app('Old Snapmaker.app','Snapmaker_Orca','2.4.0')
            with self.assertRaisesRegex(ipt.TowerError,'2.4.1'):wizard.save_orca(old,'snapmaker')
    def test_cli_keeps_mainline_export_and_snapmaker_plain_gcode(self):
        executable=self.root/'orca';executable.write_text('#!/bin/sh\n');executable.chmod(0o755)
        for branch in ('mainline','snapmaker'):
            w=wizard.Workflow();w.orca=str(executable);w.slicer_branch=branch;w.output=self.root/'out.3mf'
            with patch.object(wizard.subprocess,'Popen') as launch,patch.object(wizard,'extract_gcode',return_value=self.root/'plate_1.gcode'):
                launch.return_value.poll.return_value=0;launch.return_value.returncode=0
                w.slice(self.root/'source.3mf',branch)
                args=launch.call_args.args[0]
                self.assertEqual(branch=='mainline','--export-3mf' in args)
                self.assertEqual(branch=='snapmaker','--allow-newer-file' in args)
                self.assertEqual('1',args[args.index('--slice')+1])

    def test_reference_accepts_z_lifts_but_rejects_relative_xy(self):
        path=self.root/'ref.gcode';data='M83\nT0\n; Z: 0.2\n;TYPE:Outer wall\nG0 X100 Y100\nG91\nG1 Z1.5 F600\nG90\nG1 X110 E1\n'
        path.write_text(data);self.assertEqual([0],ipt.reference_layers(path,{0})[.2])
        path.write_text(data.replace('G1 Z1.5 F600','G3 Z1.5 I1 J0 P1'));self.assertEqual([0],ipt.reference_layers(path,{0})[.2])
        path.write_text(data.replace('G1 Z1.5 F600','G3 X110 E1'))
        with self.assertRaisesRegex(ipt.TowerError,'arc fitting'):ipt.reference_layers(path,{0})
        path.write_text(data.replace('G1 Z1.5 F600','G1 X1'))
        with self.assertRaisesRegex(ipt.TowerError,'absolute XY'):ipt.reference_layers(path,{0})

class SnapmakerGeometryTests(unittest.TestCase):
    setUp=core.ProjectTests.setUp
    tearDown=core.ProjectTests.tearDown
    fixture=core.ProjectTests.fixture
    def test_snapmaker_parts_use_legacy_feature_assignments(self):
        source,_=self.fixture();out=self.folder/'snap.3mf'
        original=source.read_bytes();manifest=ipt.Project(source,1,'snapmaker').generate(out,brim_width=0)
        with zipfile.ZipFile(out) as z:
            config=ipt.ET.fromstring(z.read(ipt.MODEL_SETTINGS));obj=config.find('object')
            self.assertNotIn('outer_wall_filament_id',ipt.metadata(obj))
            for part in obj.findall('part'):
                data=ipt.metadata(part)
                for key in ('wall_filament','sparse_infill_filament','solid_infill_filament'):self.assertEqual(data['extruder'],data[key])
                self.assertNotIn('outer_wall_filament_id',data)
        self.assertEqual(original,source.read_bytes());self.assertEqual(manifest,ipt.load_manifest(out))

if __name__=='__main__':unittest.main()
