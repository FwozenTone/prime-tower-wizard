import math,unittest
import isolated_prime_tower as ipt
import tower_wizard as wizard
import test_isolated_prime_tower as fixtures

class BrimThicknessTests(unittest.TestCase):
    setUp=fixtures.ProjectTests.setUp
    tearDown=fixtures.ProjectTests.tearDown
    fixture=fixtures.ProjectTests.fixture
    def test_limits_and_layer_rounding(self):
        source,_=self.fixture()
        for thickness in (.49,1.51,float('nan'),float('inf')):
            with self.assertRaisesRegex(ipt.TowerError,'Brim thickness'):
                ipt.Project(source).generate(self.folder/'invalid.3mf',brim_thickness=thickness)
        for target,actual in ((.5,.6),(1.5,1.6)):
            m=ipt.Project(source).generate(self.folder/f'{target}.3mf',brim_thickness=target)
            self.assertEqual(target,m['brim_thickness']);self.assertAlmostEqual(actual,m['brim_height'])
    def test_defaults_and_per_plate_values(self):
        self.assertEqual(.6,wizard.tower_options({})['brim_thickness'])
        data={'plate_options':{'1':{'brim_thickness':'1.2'},'2':{'brim_thickness':'.5'}}}
        self.assertEqual(1.2,wizard.plate_options(data,1)['brim_thickness'])
        self.assertEqual(.5,wizard.plate_options(data,2)['brim_thickness'])
        self.assertEqual(.6,wizard.plate_options({},1)['brim_thickness'])
