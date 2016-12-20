import cloudpassage
from multiprocessing.dummy import Pool as ThreadPool
import time
from utility import Utility


class HaloScans(object):
    """Initialize a CloudPassage Halo scan retrieval object

    Args:
        halo_key (str): API key for CloudPassage Halo
        halo_secret (str): API key secret for CloudPassage Halo

    Keyword Args:
        api_host (str): Hostname for Halo API.  Default is api.cloudpassage.com
        api_port (str): Port for API endpoint.  Defaults to 443
        start_timestamp (str): ISO8601-formatted string.  Defalults to now.
        max_threads (int): Max number of open threads.  Defaults to 10.
        batch_size (int): Limit the depth of the query.  Defaults to 20.
        integration_name (str): Name of the tool using this library.
        search_params (dict): Params for event query


    """
    def __init__(self, halo_key, halo_secret, **kwargs):
        self.halo_key = halo_key
        self.halo_secret = halo_secret
        self.api_host = "api.cloudpassage.com"
        self.api_port = 443
        self.start_timestamp = Utility.iso8601_now()
        self.max_threads = 10
        self.batch_size = 20
        self.last_scan_timestamp = None
        self.last_scan_id = ""
        self.scans = []
        self.halo_session = None
        self.ua = Utility.build_ua("")
        self.search_params = {}
        self.set_attrs_from_kwargs(kwargs)

    def __iter__(self):
        """Yields scans one at a time. Forever."""
        while True:
            for scan in self.get_next_batch():
                yield scan

    def build_halo_session(self):
        """Instantiates the Halo session"""
        halo_session = cloudpassage.HaloSession(self.halo_key,
                                                self.halo_secret,
                                                api_host=self.api_host,
                                                api_port=self.api_port,
                                                integration_string=self.ua)
        halo_session.authenticate_client()
        return halo_session

    def create_url_list(self):
        """We initially set the 'since' var to the start_timestamp.  The next
        statement will override that value with the last scan's timestamp, if
        one is set

        """

        base_url = "/v1/scans"
        modifiers = self.search_params
        if self.start_timestamp is not None:
            modifiers["since"] = self.start_timestamp
        if self.last_scan_timestamp is not None:
            modifiers["since"] = self.last_scan_timestamp
        url_list = Utility.create_url_batch(base_url, self.batch_size,
                                            modifiers=modifiers)
        return url_list

    def get_next_batch(self):
        """Gets the next batch of scans from the Halo API"""
        url_list = self.create_url_list()
        pages = self.get_pages(url_list)
        scans = Utility.sorted_items_from_pages(pages, "scans", "created_at")
        if scans[0]["id"] == self.last_scan_id:
            del scans[0]
        try:
            last_scan_timestamp = scans[-1]['created_at']
        except IndexError:
            print(self.last_scan_timestamp)
            time.sleep(30)
            return []
        last_scan_id = scans[-1]['id']
        self.last_scan_timestamp = last_scan_timestamp
        self.last_scan_id = last_scan_id
        return scans

    def set_attrs_from_kwargs(self, kwargs):
        arg_list = ["start_timestamp", "max_threads", "batch_size",
                    "search_params", "api_host", "api_port"]
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
