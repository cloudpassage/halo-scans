import cloudpassage
from multiprocessing.dummy import Pool as ThreadPool
from utility import Utility


class HaloScanDetails(object):
    def __init__(self, halo_key, halo_secret, **kwargs):
        self.halo_key = halo_key
        self.halo_secret = halo_secret
        self.api_host = "api.cloudpassage.com"
        self.api_port = 443
        self.max_threads = 4
        self.halo_session = None
        self.ua = Utility.build_ua("")
        self.search_params = {}
        self.set_attrs_from_kwargs(kwargs)

    def build_halo_session(self):
        """Instantiates the Halo session"""
        halo_session = cloudpassage.HaloSession(self.halo_key,
                                                self.halo_secret,
                                                api_host=self.api_host,
                                                api_port=self.api_port,
                                                integration_string=self.ua)
        halo_session.authenticate_client()
        return halo_session

    def get(self, scan_id):
        """This wraps other functions that get specific scan details"""
        session = self.build_halo_session()
        scan = cloudpassage.Scan(session)
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
        results = self.get_pages(findings)
        return Utility.items_from_pages(results, "findings")

    def set_attrs_from_kwargs(self, kwargs):
        arg_list = ["max_threads", "api_host", "api_port"]
        for arg in arg_list:
            if arg in kwargs:
                setattr(self, arg, kwargs[arg])
        if "integration_name" in kwargs:
            setattr(self, "ua", Utility.build_ua(kwargs["integration_name"]))

    def get_pages(self, url_list):
        """Magic happens here... we map pages to threads in a pool, return
        results when it's all done."""
        halo_session = self.build_halo_session()
        page_helper = cloudpassage.HttpHelper(halo_session)
        pool = ThreadPool(self.max_threads)
        results = pool.map(page_helper.get, url_list)
        pool.close()
        pool.join()
        return results
