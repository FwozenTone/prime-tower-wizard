import json,zipfile,unittest
import isolated_prime_tower as ipt
import test_isolated_prime_tower as core

class GenerationRulesTests(unittest.TestCase):
 setUp=core.ProjectTests.setUp
 tearDown=core.ProjectTests.tearDown
 fixture=core.ProjectTests.fixture
 def reference(self,initial,tail):
  lines=['G90','M83','G0 X100 Y100']
  for i in range(1,51):
   z=round(i*.2,5);tools=initial.get(z,tail)
   lines.append(f';Z:{z}')
   for t in tools:
    lines.extend([f'T{t}',';TYPE:Support interface' if t==2 else ';TYPE:Outer wall','G0 X100 Y100','G1 X110 E1'])
  p=self.folder/'reference.gcode';p.write_text('\n'.join(lines));return p
 def test_single_filament_skips_without_creating_files_or_requiring_frame(self):
  source,_=self.fixture();before=source.read_bytes();out=self.folder/'skip.3mf'
  result=ipt.Project(source).generate(out,reference_gcode=self.reference({},[0]))
  self.assertTrue(result['skipped']);self.assertFalse(out.exists());self.assertFalse(out.with_suffix('.3mf.ipt.json').exists());self.assertEqual(before,source.read_bytes())
 def test_explicit_frame_required_and_pla_can_own_petg_support_frame(self):
  source,_=self.fixture();ref=self.reference({.2:[0,2]},[0])
  with self.assertRaisesRegex(ipt.TowerError,'Select the prime tower outer wall'):
   ipt.Project(source).generate(self.folder/'bad.3mf',reference_gcode=ref)
  m=ipt.Project(source).generate(self.folder/'good.3mf',reference_gcode=ref,frame_slot=1)
  self.assertEqual('PLA',m['frame_material']);self.assertEqual([3],m['detected_support_slots'])
 def test_actual_mesh_lifetimes_and_peak_counts(self):
  source,_=self.fixture();before=source.read_bytes();ref=self.reference({.2:[0,2],.4:[0,2],.6:[0,1],.8:[1,0]},[0])
  for branch in ('mainline','snapmaker'):
   out=self.folder/(branch+'.3mf');m=ipt.Project(source,1,branch).generate(out,reference_gcode=ref,frame_slot=1)
   self.assertEqual(.8,m['tower_height']);self.assertEqual(3,len(m['lanes']))
   petg=next(a for a in m['lanes'] if a['material']=='PETG');self.assertEqual(.4,petg['height'])
   self.assertEqual(2,sum(a['material']=='PLA' for a in m['lanes']))
   self.assertEqual(m,ipt.load_manifest(out))
   with zipfile.ZipFile(out) as z:
    cfg=ipt.ET.fromstring(z.read(ipt.MODEL_SETTINGS));model=ipt.ET.fromstring(z.read(ipt.MODEL));objects={o.get('id'):o for o in model.findall('./'+ipt.Q('resources')+'/'+ipt.Q('object'))}
    part=next(p for p in cfg.find('object').findall('part') if ipt.metadata(p)['name']=='IPT_F03_material')
    vertices=objects[part.get('id')].iter(ipt.Q('vertex'))
    self.assertAlmostEqual(.4,max(float(v.get('z')) for v in vertices))
    self.assertEqual('0',ipt.metadata(cfg.find('plate'))['enable_prime_tower'])
   self.assertEqual(before,source.read_bytes())
 def test_two_same_material_tools_on_separate_layers(self):
  source,_=self.fixture();ref=self.reference({.2:[0],.4:[1],.6:[0]},[0])
  m=ipt.Project(source).generate(self.folder/'same.3mf',reference_gcode=ref,frame_slot=1)
  self.assertEqual(.6,m['tower_height']);self.assertEqual(2,len(m['lanes']))
  self.assertEqual([[0,0],[1,None],[0,None]],[r['tools'] for r in m['layer_schedule']])
 def test_reference_ignores_initial_pickup_and_auxiliaries(self):
  p=self.folder/'ref.gcode';p.write_text('G90\nM83\nT0\nG0 X1 Y1\n;Z:.2\n;TYPE:Outer wall\nG1 X2 E1\nT1\n;TYPE:Brim\nG1 X3 E1\nT0\n;Z:.4\n;TYPE:Outer wall\nG1 X4 E1\n;Z:.6\nT1\n;TYPE:Support\nG1 X5 E1')
  layers=ipt.reference_layers(p,{0,1});self.assertEqual([.6],layers.pickup_layers);self.assertEqual([0],layers[.2]);self.assertEqual([1],layers[.6])

 def test_retired_tools_do_not_restrict_later_layer_heights(self):
  source,_=self.fixture();project=ipt.Project(source)
  project.settings['min_layer_height']=['.07','.07','.2']
  lines=['G90','M83','G0 X100 Y100']
  zs=[.2,.4,.48]+[round(.48+i*.12,5) for i in range(1,80)]
  for z in zs:
   lines.append(f';Z:{z}')
   for t in ([0,2] if z<=.4 else [0,1]):lines.extend([f'T{t}',';TYPE:Outer wall','G0 X100 Y100','G1 X110 E1'])
  ref=self.folder/'retired.gcode';ref.write_text('\n'.join(lines))
  m=project.generate(self.folder/'retired.3mf',reference_gcode=ref,frame_slot=1)
  self.assertEqual(.4,next(a['height'] for a in m['lanes'] if a['material']=='PETG'))

 def test_retirement_meshes_stop_at_assigned_heights_in_both_slicers(self):
  source,_=self.fixture(3)
  ref=self.reference({.2:[0,1,2,3],.4:[0,1,3],.6:[0,3]},[0])
  for branch in ('mainline','snapmaker'):
   out=self.folder/(branch+'_retired.3mf')
   m=ipt.Project(source,1,branch).generate(out,reference_gcode=ref,frame_slot=1)
   self.assertEqual(['PETG','PLA','PLA','PLA'],[a['material'] for a in m['lanes']])
   self.assertEqual([.6,.4,.2,.8],[a['height'] for a in m['lanes']])
   with zipfile.ZipFile(out) as z:
    cfg=ipt.ET.fromstring(z.read(ipt.MODEL_SETTINGS));model=ipt.ET.fromstring(z.read(ipt.MODEL))
    objects={o.get('id'):o for o in model.findall('./'+ipt.Q('resources')+'/'+ipt.Q('object'))}
    vertices=[]
    for part in cfg.find('object').findall('part'):
     if ipt.metadata(part)['name'].endswith('_material'):
      vertices.extend(tuple(float(v.get(k)) for k in ('x','y','z')) for v in objects[part.get('id')].iter(ipt.Q('vertex')))
    # Mesh coordinates are local to the assembly; manifest bounds are on-plate.
    ymin=min(a['bounds'][1] for a in m['lanes'])
    for a in m['lanes']:
     lo=a['bounds'][1]-ymin+ipt.WALL;hi=a['bounds'][3]-ymin+ipt.WALL
     zs=[v[2] for v in vertices if lo+1e-5<v[1]<hi-1e-5]
     self.assertTrue(zs);self.assertAlmostEqual(a['height'],max(zs),places=5)
    settings=json.loads(z.read(ipt.SETTINGS))
    self.assertEqual('0',settings['enable_prime_tower']);self.assertEqual('0',settings['independent_support_layer_height'])
    self.assertIn('enable_prime_tower',settings['different_settings_to_system'][0])
    self.assertIn('independent_support_layer_height',settings['different_settings_to_system'][0])
