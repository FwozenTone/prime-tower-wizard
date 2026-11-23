import unittest
from collections import Counter
import isolated_prime_tower as ipt
from brim_geometry import make_brim,make_gussets,geometry_library
import test_multimaterial as material_tests

class ReinforcementGeometryTests(unittest.TestCase):
    def test_gussets_closed_bonded_and_inside_brim(self):
        geometry_library()
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        for rib,width in ((5,5),(20,20),(25,5)):
            frame,_=ipt.geometry(2,80,30,rib,5,3)
            brim=make_brim(frame,width,.6)
            fins,details=make_gussets(frame,width,.6,80,31.6,11.6)
            self.assertEqual(8,len(details));self.assertEqual(64,len(fins))
            self.assertTrue(all(g["run"]==width and g["height"]==2*width for g in details))
            footprint=unary_union([Polygon([(x,y) for x,y,z in t]) for t in frame if all(p[2]==0 for p in t)])
            brimfoot=unary_union([Polygon([(x,y) for x,y,z in t]) for t in brim if all(p[2]==0 for p in t)])
            for i in range(0,len(fins),8):
                part=fins[i:i+8]
                edges=Counter(tuple(sorted((a,b))) for t in part for a,b in zip(t,t[1:]+t[:1]))
                self.assertTrue(all(v==2 for v in edges.values()))
                plan=unary_union([Polygon([(x,y) for x,y,z in t]) for t in part])
                self.assertGreater(plan.intersection(footprint).area,0)
                self.assertGreater(plan.intersection(brimfoot).area,0)
                self.assertLess(plan.difference(footprint.union(brimfoot)).area,.001)
                self.assertLess(min(p[2] for t in part for p in t),.6)
                for k in range(2):
                    lane=Polygon([(.8,.8+5*k),(30.8,.8+5*k),(30.8,5.8+5*k),(.8,5.8+5*k)])
                    self.assertLess(plan.intersection(lane).area,1e-8)
    def test_gusset_height_stops_at_tower_top(self):
        frame,_=ipt.geometry(2,25,30,20,5,3)
        fins,details=make_gussets(frame,20,.6,25,31.6,11.6)
        self.assertEqual(8,len(details))
        self.assertTrue(all(g['run']==20 and g['top_z']==25 for g in details))
        self.assertAlmostEqual(25,max(p[2] for t in fins for p in t))

    def test_no_brim_or_short_tower_omits_fins(self):
        self.assertEqual(([],[]),make_gussets([],0,.6,80,30,10))
        self.assertEqual(([],[]),make_gussets([],5,.6,.6,30,10))

class ReinforcedProjectTests(unittest.TestCase):
    setUp=material_tests.MultiMaterialTests.setUp
    tearDown=material_tests.MultiMaterialTests.tearDown
    fixture=material_tests.MultiMaterialTests.fixture
    reference=material_tests.MultiMaterialTests.reference
    def test_three_variable_layers_and_both_branches(self):
        source,_=self.fixture()
        rows=[(.2,[0,1,2]),(.35,[0,1,2]),(.6,[0,1,2])]+[(round(.6+i*.2,5),[0,1,2]) for i in range(1,48)]
        ref=self.reference(rows)
        for branch in ('mainline','snapmaker'):
            m=ipt.Project(source,1,branch).generate(self.folder/(branch+'.3mf'),reference_gcode=ref)
            self.assertEqual(3,m['brim_layers']);self.assertAlmostEqual(.6,m['brim_height'])
            self.assertEqual(8,len(m['gussets']));self.assertEqual(0,m['placement_rotation'])
            self.assertTrue(all(g['thickness']==1.2 for g in m['gussets']))
    def test_three_constant_layers(self):
        source,_=self.fixture();p=ipt.Project(source);p.settings.update(initial_layer_print_height='.25',layer_height='.15')
        m=p.generate(self.folder/'constant.3mf')
        self.assertEqual(4,m['brim_layers']);self.assertAlmostEqual(.7,m['brim_height'])
