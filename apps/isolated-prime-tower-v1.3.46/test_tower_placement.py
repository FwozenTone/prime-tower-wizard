from test_generation_fixture import generate_fixture
import unittest
import isolated_prime_tower as ipt

class PlacementTests(unittest.TestCase):
    def project(self):
        p=ipt.Project.__new__(ipt.Project)
        p.settings={'printable_area':['0x0','200x0','200x200','0x200']}
        p.reference_bounds=[60,20,0,110,110,100]
        p.items=[];p.objects={}
        return p
    def test_brim_must_stay_inside_bed(self):
        p=self.project()
        with self.assertRaisesRegex(ipt.TowerError,'outside the bed'):
            p.place([-20,-20,0,50,50,.2],(10,10),4)
    def test_brim_can_extend_below_upper_overhang(self):
        p=self.project()
        args=dict(frame_bounds=[0,0,0,30,30,100],layer_bounds={.2:[100,100,110,110],10:[60,20,90,70]},first_layer=.2,tower_height=100)
        self.assertEqual((25,25),p.place([-20,-20,0,50,50,.2],(25,25),4,**args))
        args['layer_bounds'][.2]=[60,20,90,70]
        with self.assertRaises(ipt.TowerError):p.place([-20,-20,0,50,50,.2],(25,25),4,**args)
    def test_reference_brim_paths_are_retained_for_placement(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'reference.gcode'
            path.write_text('M83\nT0\n; Z: 0.2\n;TYPE:Brim\nG0 X10 Y10\nG1 X50 E1\n;TYPE:Outer wall\nG0 X20 Y20\nG1 X30 E1\n')
            layers=ipt.reference_layers(path,{0})
            self.assertEqual([10.,10.,50.,20.],layers.extrusion_bounds[.2])
            self.assertEqual([0],layers[.2])

class InitialPlacementTests(unittest.TestCase):
    def test_fixed_front_corner_offset_without_search_or_rotation(self):
        from unittest.mock import patch
        import test_isolated_prime_tower as fixtures
        case=fixtures.ProjectTests();case.setUp()
        try:
            source,_=case.fixture();out=case.folder/'placed.3mf'
            project=ipt.Project(source)
            bed=[tuple(map(float,v.split('x'))) for v in project.settings['printable_area']]
            with patch.object(ipt.Project,'place',side_effect=AssertionError('Placement search must not run')):
                manifest=generate_fixture(project,out,brim_width=20,rib_size=20)
            self.assertEqual(0,manifest['placement_rotation'])
            self.assertEqual(manifest,ipt.load_manifest(out))
            self.assertAlmostEqual(min(x for x,y in bed)+8,manifest['assembly_bounds'][0])
            self.assertAlmostEqual(min(y for x,y in bed)+8,manifest['assembly_bounds'][1])
        finally:case.tearDown()
