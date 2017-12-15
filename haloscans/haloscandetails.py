import cloudpassage
from halo_general import HaloGeneral
from utility import Utility


class HaloScanDetails(object):
    def __init__(self, halo_key, halo_secret, **kwargs):
        self.halo_key = halo_key
        self.halo_secret = halo_secret
        self.api_host = "api.cloudpassage.com"
        self.api_port = 443
        self.max_threads = 2
        self.halo_session = None
        self.ua = Utility.build_ua("")
        self.search_params = {}
        self.set_attrs_from_kwargs(kwargs)

    def get(self, scan_id):
        """This wraps other functions that get specific scan details"""
        scan = cloudpassage.Scan(self.halo_session)
        details = scan.scan_details(scan_id)
        if details["module"] == "fim":
            new_deets = self.enrich_fim(details)
            details["findings"] = None
            details["findings"] = new_deets
        return details

    def enrich_fim(self, scan_document):
        findings = []
        for finding in scan_document["findings"]:
            findings_url = "/v1/scans/%s/findings/%s" % (scan_document["id"],
                                                         finding["id"])
            findings.append(findings_url)
        results = HaloGeneral.get_pages(self.halo_key, self.halo_secret,
                                        self.api_host, self.api_port, self.ua,
                                        self.max_threads, findings)
        return Utility.items_from_pages(results, "findings")

    def set_attrs_from_kwargs(self, kwargs):
        arg_list = ["max_threads", "api_host", "api_port"]
        for arg in arg_list:
            if arg in kwargs:
                setattr(self, arg, kwargs[arg])
        if "integration_name" in kwargs:
            setattr(self, "ua", Utility.build_ua(kwargs["integration_name"]))

    def set_halo_session(self):
        self.halo_session = HaloGeneral.build_halo_session(self.halo_key,
                                                           self.halo_secret,
                                                           self.api_host,
                                                           self.api_port,
                                                           self.ua)
