import imp
import os
import sys

module_name = 'haloscans'
here_dir = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(here_dir, '../../')
sys.path.append(module_path)
fp, pathname, description = imp.find_module(module_name)
haloscans = imp.load_module(module_name, fp, pathname, description)


class TestUnitHaloScans:
    def test_unit_haloscans_instantiate(self):
        assert haloscans.HaloScans("", "")
