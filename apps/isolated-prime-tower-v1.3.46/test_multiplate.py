from test_generation_fixture import generate_fixture
"""Regression checks for independent towers in one multi-plate project."""
import json, math, unittest, zipfile
from unittest.mock import patch
import xml.etree.ElementTree as ET
import isolated_prime_tower as ipt
import tower_wizard as wizard
import test_isolated_prime_tower as core

class MultiPlateTests(unittest.TestCase):
    setUp=core.ProjectTests.setUp
    tearDown=core.ProjectTests.tearDown
    fixture=core.ProjectTests.fixture

    def project(self,count=3):
        path,files=self.fixture(count)
        root=ET.fromstring(files[ipt.MODEL]);config=ET.fromstring(files[ipt.MODEL_SETTINGS])
        first=config.find('plate');instances=list(first.findall('model_instance'))
        items=root.find(ipt.Q('build'));cols=math.ceil(math.sqrt(count))
        for i,instance in enumerate(instances):
            plate=first if i==0 else ET.SubElement(config,'plate')
            if i: first.remove(instance);plate.append(instance)
            ipt.set_meta(plate,'plater_id',i+1)
            transform=list(map(float,items[i].get('transform').split()))
            transform[9]+=(i%cols)*420;transform[10]-=(i//cols)*420
            items[i].set('transform',' '.join(map(str,transform)))
        files[ipt.MODEL]=ipt.xml_bytes(root);files[ipt.MODEL_SETTINGS]=ipt.xml_bytes(config)
        self.write(path,files)
        return path,files

    def write(self,path,files):
        with zipfile.ZipFile(path,'w') as z:
            for name,data in files.items():z.writestr(name,data)

    def read(self,path):
        with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}

    def test_accumulates_towers_on_own_plates_and_preserves_originals(self):
        source,original=self.project();current=source;expected={}
        for plate in (2,3,1):
            output=self.folder/f'added_{plate}.3mf'
            expected[plate]=generate_fixture(ipt.Project(current,plate),output,filaments=[plate,4])
            current=output
            self.assertEqual(expected[plate],ipt.load_manifest(current,plate))
            with self.assertRaisesRegex(ipt.TowerError,'already contains'):ipt.Project(current,plate)
        self.assertEqual([True]*3,[p['has_tower'] for p in wizard.plates(current)])
        with self.assertRaisesRegex(ipt.TowerError,'--plate'):ipt.load_manifest(current)
        for plate,manifest in expected.items():self.assertEqual(manifest,ipt.load_manifest(current,plate))
        files=self.read(current);root=ET.fromstring(files[ipt.MODEL]);cfg=ET.fromstring(files[ipt.MODEL_SETTINGS])
        before=ET.fromstring(original[ipt.MODEL]);old_items={i.get('objectid'):ET.tostring(i) for i in before.find(ipt.Q('build'))}
        for item in root.find(ipt.Q('build')):
            if item.get('objectid') in old_items:self.assertEqual(old_items[item.get('objectid')],ET.tostring(item))
        for i,plate in enumerate(cfg.findall('plate'),1):
            members={ipt.metadata(m)['object_id'] for m in plate.findall('model_instance')}
            self.assertEqual(2,len(members))
            first=next(item for item in root.find(ipt.Q('build')) if item.get('objectid') in members)
            obj=next(o for o in cfg.findall('object') if o.get('id')==first.get('objectid'))
            self.assertEqual(f'IPT_ASSEMBLY_PLATE_{i}',ipt.metadata(obj)['name'])
        self.assertEqual(original,self.read(source))

    def test_orca_saved_project_detects_tower_without_embedded_manifest(self):
        source,_=self.project();first=self.folder/'first.3mf'
        generate_fixture(ipt.Project(source,2),first,filaments=[2,4])
        files=self.read(first);del files[ipt.MANIFEST]
        saved=self.folder/'saved.3mf';self.write(saved,files)
        self.assertEqual([False,True,False],[p['has_tower'] for p in wizard.plates(saved)])
        ipt.Project(saved,1)
        with self.assertRaisesRegex(ipt.TowerError,'already contains'):ipt.Project(saved,2)

    def test_legacy_manifest_and_assembly_name_survive_adding_other_plate(self):
        source,_=self.project();first=self.folder/'legacy.3mf'
        m=generate_fixture(ipt.Project(source,2),first,filaments=[2,4]);files=self.read(first)
        for n in (ipt.MODEL,ipt.MODEL_SETTINGS):files[n]=files[n].replace(b'IPT_ASSEMBLY_PLATE_2',b'IPT_ASSEMBLY')
        m['assembly_name']='IPT_ASSEMBLY';files[ipt.MANIFEST]=json.dumps(m).encode();self.write(first,files)
        combined=self.folder/'combined.3mf';generate_fixture(ipt.Project(first,1),combined,filaments=[1,4])
        self.assertEqual(m,ipt.load_manifest(combined,2))

    def test_setup_rejects_occupied_selection_but_accepts_other_plates(self):
        source,_=self.project();first=self.folder/'first.3mf';generate_fixture(ipt.Project(source,2),first,filaments=[2,4])
        w=wizard.Workflow()
        with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'):
            with self.assertRaisesRegex(ipt.TowerError,'already contain'):w.setup({'source':str(first),'plates':[1,2]})
            w.setup({'source':str(first),'plates':[1,3]})
        self.assertEqual([1,3],w.selected_plates)

    def reference(self,plate):
        path=self.folder/f'reference_{plate}.gcode';lines=['M83','G0 X100 Y100']
        for i in range(1,51):
            lines.append(f'; Z: {i*.2:.2f}')
            for tool in (plate-1,3):lines += [f'T{tool}',';TYPE:Outer wall','G0 X100 Y100','G1 X110 E1']
        path.write_text('\n'.join(lines));return path

    def test_batch_continues_after_reference_failure_and_combines_successes(self):
        source,_=self.project();w=wizard.Workflow();calls=[]
        def sliced(project,tag):
            calls.append(w.plate)
            if w.plate==2:raise ipt.TowerError('test slice failure')
            return self.reference(w.plate)
        with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=sliced):
            w.automatic({'source':str(source),'plates':[1,2,3],'frame_slot':4,'open_after':False})
        self.assertEqual([1,2,3],calls)
        self.assertEqual([True,False,True],[p['has_tower'] for p in wizard.plates(w.output)])
        self.assertEqual('batch_complete',w.state['stage'])
        self.assertEqual([True,False,True],[r['generated'] for r in w.state['result']['plates']])
        self.assertEqual(1,ipt.load_manifest(w.output,1)['plate_number'])
        self.assertEqual(3,ipt.load_manifest(w.output,3)['plate_number'])

    def test_batch_continues_after_geometry_failure_without_auditing(self):
        source,_=self.project();w=wizard.Workflow();original_generate=ipt.Project.generate;audited=[]
        def generate(project,*args,**kwargs):
            if project.plate_number==2:raise ipt.TowerError('test geometry failure')
            return original_generate(project,*args,**kwargs)
        def audit(gcode,manifest):
            audited.append(manifest['plate_number'])
            if manifest['plate_number']==1:raise ipt.TowerError('test audit failure')
            return {'passed':True}
        with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=lambda *args:self.reference(w.plate)),patch.object(ipt.Project,'generate',generate),patch.object(ipt,'audit',side_effect=audit):
            w.automatic({'source':str(source),'plates':[1,2,3],'frame_slot':4,'open_after':False,'run_validation':True})
        self.assertEqual([],audited)
        self.assertEqual(['not requested',None,'not requested'],[r.get('validation') for r in w.state['result']['plates']])
        self.assertEqual([True,False,True],[p['has_tower'] for p in wizard.plates(w.output)])

    def test_per_plate_options_reach_each_generated_tower(self):
        source,_=self.project();w=wizard.Workflow()
        choices={'1':{'width':40,'rib_size':8,'brim_width':2,'purge_volume':7,'frame_slot':1},
                 '3':{'width':35,'rib_size':6,'brim_width':3,'purge_volume':6,'frame_slot':4}}
        with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=lambda *args:self.reference(w.plate)):
            w.automatic({'source':str(source),'plates':[1,3],'plate_options':choices,'open_after':False})
        for plate in (1,3):
            manifest=ipt.load_manifest(w.output,plate)
            for key,value in choices[str(plate)].items():self.assertEqual(value,manifest[key])
            self.assertIsNone(manifest['support_slot'])

    def test_unspecified_plate_defaults_do_not_inherit_another_plate(self):
        data={'width':99,'plate_options':{'1':{'width':40,'support_slot':4}}}
        self.assertEqual(40,wizard.plate_options(data,1)['width'])
        self.assertIsNone(wizard.plate_options(data,1)['support_slot'])
        self.assertEqual(wizard.tower_options({}),wizard.plate_options(data,3))

    def test_invalid_first_plate_settings_do_not_stop_later_plates(self):
        source,_=self.project();w=wizard.Workflow()
        with patch.object(wizard,'save_orca',return_value='orca'),patch.object(wizard,'save_source_folder'),patch.object(w,'slice',side_effect=lambda *args:self.reference(w.plate)):
            w.automatic({'source':str(source),'plates':[1,3],'plate_options':{'1':{'width':'invalid'},'3':{'frame_slot':4}},'open_after':False})
        self.assertEqual([False,True],[r['generated'] for r in w.state['result']['plates']])
        self.assertEqual(30,ipt.load_manifest(w.output,3)['width'])

if __name__=='__main__':unittest.main()
