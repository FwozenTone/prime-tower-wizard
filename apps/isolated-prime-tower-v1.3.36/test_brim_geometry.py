import unittest
from collections import Counter
from brim_geometry import make_brim,geometry_library
import isolated_prime_tower as ipt

class BrimTests(unittest.TestCase):
    def test_width_height_closed_mesh_and_clear_lanes(self):
        geometry_library()
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        for width in (2.,7.):
            frame,lanes=ipt.geometry(2,5,width=30,rib=5,lane=5)
            triangles=make_brim(frame,width,.25)
            self.assertEqual({0.,.25},{p[2] for t in triangles for p in t})
            b=ipt.bounds(frame);bb=ipt.bounds(triangles)
            for axis in (0,1):
                self.assertAlmostEqual(b[axis]-width,bb[axis],places=3)
                self.assertAlmostEqual(b[axis+3]+width,bb[axis+3],places=3)
            edges=Counter(tuple(sorted((a,b))) for t in triangles for a,b in zip(t,t[1:]+t[:1]))
            self.assertTrue(all(n==2 for n in edges.values()))
            bottom=unary_union([Polygon([(x,y) for x,y,z in t]) for t in triangles if all(p[2]==0 for p in t)])
            for lane in lanes:
                b=ipt.bounds(lane);interior=Polygon([(b[0],b[1]),(b[3],b[1]),(b[3],b[4]),(b[0],b[4])])
                self.assertLess(bottom.intersection(interior).area,1e-6)
            footprint=unary_union([Polygon([(x,y) for x,y,z in t]) for t in frame if all(p[2]==0 for p in t)])
            self.assertEqual(0.,bottom.distance(footprint))
            self.assertGreater(bottom.intersection(footprint).area,0.)
    def test_zero_width(self):
        self.assertEqual([],make_brim([],0,.2))
