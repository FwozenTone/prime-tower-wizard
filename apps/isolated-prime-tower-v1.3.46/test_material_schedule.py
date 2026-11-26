import unittest
from material_schedule import plan_areas

class MaterialScheduleTests(unittest.TestCase):
 def check(self,layers,materials,frame,height):
  areas,rows=plan_areas(layers,materials,frame,height)
  for row in rows:
   owners=row['tools']
   for tool in row['reference_tools']:
    self.assertIn(tool,owners)
   for a,t in zip(areas,owners):
    if row['z']>a['height']:self.assertIsNone(t)
    else:self.assertEqual(a['material'],materials[t+1])
  return areas,rows
 def test_peak_counts_include_all_filaments_not_all_slots(self):
  layers={.2:[0,1,5],.4:[2,3,5],.6:[4,5]}
  mats={1:'PLA',2:'PLA',3:'PLA',4:'PLA',5:'PLA',6:'PETG'}
  areas,rows=self.check(layers,mats,6,.6)
  self.assertEqual(['PLA','PLA','PETG'],[a['material'] for a in areas])
  self.assertEqual([4,None,5],rows[-1]['tools'])
 def test_two_same_type_alternating_layers_have_two_areas(self):
  areas,rows=self.check({.2:[0],.4:[1],.6:[0]},{1:'PLA',2:'PLA'},1,.6)
  self.assertEqual(2,len(areas));self.assertEqual([[0,0],[1,None],[0,None]],[r['tools'] for r in rows])
 def test_frame_peak_also_counts_and_inactive_sections_are_maintained(self):
  areas,rows=self.check({.2:[0,1,2],.4:[2],.6:[1,2]},{1:'PLA',2:'PLA',3:'PETG'},1,.6)
  self.assertEqual(2,sum(a['material']=='PLA' for a in areas))
  self.assertEqual(2,sum(t is not None for t in rows[1]['tools']))
 def test_temporary_gap_and_permanent_end(self):
  layers={.2:[0,1],.4:[0],.6:[0,1],.8:[0,2],1.:[0,2]}
  areas,rows=self.check(layers,{1:'PLA',2:'PETG',3:'ABS'},1,1.)
  i=next(i for i,a in enumerate(areas) if a['material']=='PETG')
  self.assertEqual([1,1,1,None,None],[r['tools'][i] for r in rows])
  self.assertEqual(.6,areas[i]['height'])
 def test_shell_type_does_not_expire(self):
  areas,rows=self.check({.2:[0,1],.4:[1,2],.6:[1,2]},{1:'PLA',2:'PETG',3:'PETG'},1,.6)
  i=next(i for i,a in enumerate(areas) if a['material']=='PLA')
  self.assertEqual(.6,areas[i]['height']);self.assertTrue(all(r['tools'][i]==0 for r in rows))
 def test_material_used_after_tower_end_is_not_retired_early(self):
  areas,rows=self.check({.2:[0,1],.4:[0],.6:[1],.8:[1]},{1:'PLA',2:'PETG'},1,.6)
  self.assertTrue(all(a['height']==.6 for a in areas))
