import math
import unittest
import isolated_prime_tower as ipt

class PrimingPathTests(unittest.TestCase):
 def test_volume_capacity(self):
  for width in (10.,20.,30.):
   for height in (.08,.12,.2,.3):
    for volume in (5.,15.,45.):
     depth,loops=ipt.lane_dimensions(width,volume,height)
     from brim_geometry import braced_loop_mesh,geometry_library
     geometry_library()
     from shapely.geometry import Polygon
     from shapely.ops import unary_union
     ts=braced_loop_mesh(width,depth,10.,ipt.WALL,loops,ipt.rounded,0.,0.)
     area=unary_union([Polygon([(x,y) for x,y,z in tri]) for tri in ts if all(v[2]==10. for v in tri)]).area
     self.assertGreaterEqual(loops,1)
     self.assertGreaterEqual(.85*height*area+1e-6,volume)
     self.assertLessEqual((depth-2*ipt.WALL-loops*ipt.WALL)/(loops+1),6.+1e-6)
 def test_loop_contacts_both_side_walls_and_stays_in_lane(self):
  for width in (10.,20.,30.):
   depth,runs=ipt.lane_dimensions(width,5.,.12)
   _,lanes=ipt.geometry(2,10.,width,5.,depth,runs)
   for i,triangles in enumerate(lanes):
    b=ipt.bounds(triangles[12:])
    self.assertAlmostEqual(b[0],ipt.WALL,places=5)
    self.assertAlmostEqual(b[3],ipt.WALL+width,places=5)
    self.assertAlmostEqual(b[1],ipt.WALL+i*depth,places=5)
    self.assertAlmostEqual(b[4],ipt.WALL+(i+1)*depth,places=5)
 def test_loop_slabs_are_closed(self):
  depth,runs=ipt.lane_dimensions(20.,5.,.12)
  _,lanes=ipt.geometry(1,10.,20.,5.,depth,runs)
  triangles=ipt.lane_slab(lanes[0],10.,2.,2.12)
  from collections import Counter
  edges=Counter()
  for tri in triangles:
   for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((a,b)))]+=1
  self.assertTrue(all(count==2 for count in edges.values()))

 def test_frame_never_overlaps_prime_loop(self):
  from brim_geometry import geometry_library
  geometry_library()
  from shapely.geometry import Polygon
  from shapely.ops import unary_union
  def section(ts):
   return unary_union([Polygon([(x,y) for x,y,z in tri]) for tri in ts if all(abs(v[2]-10)<1e-8 for v in tri)])
  for width in (10.,20.,30.):
   for rib in (5.,20.):
    depth,runs=ipt.lane_dimensions(width,5.,.12)
    frame,lanes=ipt.geometry(2,10.,width,rib,depth,runs)
    f=section(frame)
    for lane in lanes:
     p=section(lane)
     self.assertLess(f.intersection(p).area,1e-5)
     self.assertLess(f.distance(p),1e-5)
