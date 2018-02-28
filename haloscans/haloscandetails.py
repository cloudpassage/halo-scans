import cloudpassage
import time
from halo_general import HaloGeneral
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

    def get(self, scan_id):
        """This wraps other functions that get specific scan details"""
        scan = cloudpassage.Scan(self.halo_session)
        details = scan.scan_details(scan_id)
        details = self.hold_for_completion(details)
        if details["module"] == "fim":
            new_deets = self.enrich_fim(details)
            details["findings"] = None
            details["findings"] = new_deets
        return details

    def hold_for_completion(self, scan_body):
        """Wait for completion and return completed scan.

        This function checks the status from scan_body and if the status is
        queued, pending, or running, we wait and re-query until the status
        indicates completion.

        We don't wait more than 6 minutes for a scan to complete, though.

        Args:
            scan_body(dict): Body of scan from API.

        """
        wait_time = 20
        scan = cloudpassage.Scan(self.halo_session)
        time_waited = 0
        while scan_body["status"] in ["queued", "pending", "running"]:
            if time_waited == 300:
                print("Scan with ID %s for server %s has been in hold_for_completion for more than 5 minutes!" % (scan_body["id"], scan_body["server_id"]))  # NOQA
            elif time_waited == 360:
                print("Not waiting on scan with ID %s anymore..." % scan_body["id"])  # NOQA
                break
            time.sleep(wait_time)
            time_waited += wait_time
            scan_body = scan.scan_details(scan_body["id"])
        return scan_body

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
