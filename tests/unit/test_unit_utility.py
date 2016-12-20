import imp
import os
import sys

module_name = 'haloscans'
here_dir = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(here_dir, '../../')
sys.path.append(module_path)
fp, pathname, description = imp.find_module(module_name)
haloscans = imp.load_module(module_name, fp, pathname, description)


class TestUnitUtility:
    def test_utility_8601_now(self):
        assert isinstance(haloscans.Utility.iso8601_now(), str)

    def test_unit_utility_build_ua(self):
        assert isinstance(haloscans.Utility.build_ua(""), str)

    def test_unit_utility_build_ua_2(self):
        canary = "canary"
        assert canary in haloscans.Utility.build_ua(integration_name=canary)

    def test_unit_utility_create_url_batch(self):
        baseurl = "/v1/scans"
        batch_size = 50
        modifiers = {"hello": "world"}
        url_list = haloscans.Utility.create_url_batch(baseurl, batch_size,
                                                      modifiers)
        assert batch_size == len(url_list)
        for url in url_list:
            assert modifiers["hello"] in url

    def test_unit_utility_sort_pages(self):
        pagination_key = "scans"
        sort_field = "number"
        page_1 = {pagination_key: [{sort_field: 1},
                                   {sort_field: 2},
                                   {sort_field: 5}]}
        page_2 = {pagination_key: [{sort_field: 6},
                                   {sort_field: 3},
                                   {sort_field: 4}]}
        inbound = [page_1, page_2]
        expected = [{sort_field: 1}, {sort_field: 2},
                    {sort_field: 3}, {sort_field: 4},
                    {sort_field: 5}, {sort_field: 6}]
        actual = haloscans.Utility.sorted_items_from_pages(inbound,
                                                           pagination_key,
                                                           sort_field)
        assert expected == actual
