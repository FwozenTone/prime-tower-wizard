import random,unittest
from material_schedule import plan_areas

class AreaRetirementTests(unittest.TestCase):
 def verify(self,layers,mats,frame,height):
  areas,rows=plan_areas(layers,mats,frame,height);kinds=set(mats.values());first=min(layers)
  self.assertGreaterEqual(len(areas),2)
  for kind in kinds:
   indices=[i for i,a in enumerate(areas) if a['material']==kind]
   self.assertEqual(indices,list(range(min(indices),max(indices)+1)))
   peak=max(len({t for t in used if mats[t+1]==kind}) for used in layers.values())
   self.assertEqual(len(indices),max(peak,2 if len(kinds)==1 else 1))
   priority=sorted(indices,key=lambda i:(min(i,len(areas)-1-i),i));previous=set(indices)
   for row in rows:
    active={i for i in indices if row['tools'][i] is not None}
    future=max(len({t for t in used if mats[t+1]==kind}) for z,used in layers.items() if z>=row['z'])
    count=max(future,1 if kind==mats[frame] else 0)
    if row['z']==first:count=len(indices)
    self.assertEqual(active,set(priority[:count]));self.assertLessEqual(active,previous);previous=active
    for i in active:self.assertEqual(mats[row['tools'][i]+1],kind)
   for i in indices:self.assertEqual(areas[i]['height'],max(r['z'] for r in rows if r['tools'][i] is not None))
  for row in rows:
   self.assertLessEqual(set(row['reference_tools']),set(row['tools']))
   for kind in kinds:
    active={t for t in row['reference_tools'] if mats[t+1]==kind}
    if active:
     self.assertTrue(all(t in active for i,t in enumerate(row['tools']) if t is not None and areas[i]['material']==kind))
  return areas,rows
 def test_twelve_tools_arbitrary_drop_and_temporary_rebound(self):
  mats={i:'PLA' for i in range(1,13)}
  layers={.2:list(range(12)),.4:[0],.6:list(range(8)),.8:[0,1],1.:[1],1.2:[0]}
  areas,rows=self.verify(layers,mats,1,1.2)
  self.assertEqual([12,8,8,2,1,1],[sum(t is not None for t in r['tools']) for r in rows])
  self.assertEqual({0,11},{i for i,t in enumerate(rows[3]['tools']) if t is not None})
 def test_frame_survives_absence_other_types_retire(self):
  mats={1:'PLA',2:'PLA',3:'PETG',4:'PETG',5:'TPU',6:'TPU'}
  self.verify({.2:[0,1,2,3,4,5],.4:[2],.6:[2,4],.8:[3],1.:[2]},mats,1,1.)
 def test_two_area_base_alternating_single_area_above(self):
  a,r=self.verify({.2:[0],.4:[1],.6:[0],.8:[1]},{1:'PLA',2:'PLA'},1,.8)
  self.assertEqual([.8,.2],[x['height'] for x in a])
 def test_demand_looks_beyond_tower_end(self):
  self.verify({.2:[0,1,2],.4:[0],.6:[1],.8:[2]},{1:'PLA',2:'PETG',3:'PETG'},1,.4)
 def test_generated_schedules_across_material_combinations(self):
  rng=random.Random(46)
  for case in range(150):
   n=rng.randint(2,12);k=rng.randint(1,min(4,n));mats={i:['PLA','PETG','ABS','TPU'][(i-1)%k] for i in range(1,n+1)}
   layers={.2:list(range(n))}
   for j in range(2,12):layers[round(j*.2,2)]=rng.sample(range(n),rng.randint(1,n))
   self.verify(layers,mats,1,2.2)
