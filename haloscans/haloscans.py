import cloudpassage
import sys
import threading
import time
from collections import deque
from halo_general import HaloGeneral
from haloscandetails import HaloScanDetails
from multiprocessing.dummy import Pool as ThreadPool
from utility import Utility


class HaloScans(object):
    """Initialize a CloudPassage Halo scan retrieval object

    Args:
        halo_key (str): API key for CloudPassage Halo
        halo_secret (str): API key secret for CloudPassage Halo

    Keyword Args:
        api_host (str): Hostname for Halo API.  Default is api.cloudpassage.com
        api_port (str): Port for API endpoint.  Defaults to 443
        max_threads (int): Max number of open threads.  Defaults to 10.
        batch_size (int): Limit the depth of the query.  Defaults to 20.
        integration_name (str): Name of the tool using this library.
        search_params (dict): Params for event query
        report_performance (bool): Report performance metrics to stdout.
            Defaults to False


    """
    def __init__(self, halo_key, halo_secret, **kwargs):
        self.halo_key = halo_key
        self.halo_secret = halo_secret
        self.api_host = "api.cloudpassage.com"
        self.api_port = 443
        self.max_threads = 10
        self.batch_size = 30
        self.last_scan_timestamp = None
        self.currently_enriching = 0
        self.scans_processed = 0
        self.scans_unprocessed = deque([])
        self.completed_scans = deque([])
        self.report_performance = False
        self.halo_session = None
        self.ua = Utility.build_ua("")
        self.search_params = {"since": Utility.iso8601_now(),
                              "sort_by": "created_at.asc"}
        self.kwargs = kwargs
        self.set_attrs_from_kwargs(kwargs)
        if "start_timestamp" in kwargs:
            self.search_params["since"] = kwargs["start_timestamp"]

    def __iter__(self):
        """Yields scans one at a time. Forever.

        This iterator starts three threads: one for consuming scan metadata
        from the Halo API (/v1/scans endpoint), one for enriching those scans
        (getting scan results by ID, including recursive calls for FIM issues)
        and a thread for performance monitoring, which periodically prints
        various metrics about the iterator's (and supporting threads')
        performance and queue depth.

        It may take a couple of minutes to get the first results back from the
        iterator, due to the enricher's need to recursively query the Halo API
        for detailed scan information... so please be patient.
        """
        self.halo_session = HaloGeneral.build_halo_session(self.halo_key,
                                                           self.halo_secret,
                                                           self.api_host,
                                                           self.api_port,
                                                           self.ua)
        # First, we start the ingestion thread
        ingest = threading.Thread(target=self.scan_id_preloader)
        ingest.daemon = True
        ingest.start()
        # Next, we start the enrichment thread.
        enrich = threading.Thread(target=self.scan_enricher)
        enrich.daemon = True
        enrich.start()
        # Next, we start the performance reporter thread.
        performance = threading.Thread(target=self.performance_reporter)
        performance.daemon = True
        performance.start()
        while True:
            # If any threads die, we exit, printing the appropriate message.
            healthy = True
            if not ingest.is_alive():
                healthy = False
                print("Ingestion thread is dead!")
            elif not enrich.is_alive():
                healthy = False
                print("Enrichment thread is dead!")
            elif not performance.is_alive():
                healthy = False
                print("Performance monitoring thread is dead!")
            if not healthy:
                print("Timestamp from last scan processed: %s" %
                      self.last_scan_timestamp)
                sys.exit(1)
            # Now, we yield a scan if any are waiting.
            try:
                current_scan = self.completed_scans.popleft()
                self.last_scan_timestamp = current_scan["created_at"]
                self.scans_processed += 1
                yield current_scan
            except IndexError:
                time.sleep(1)

    def scan_id_preloader(self):
        """Get scan metadata from /v1/scans endpoint, load ids into queue."""
        scan_streamer = cloudpassage.TimeSeries(self.halo_session,
                                                self.search_params["since"],
                                                "/v1/scans", "scans",
                                                {"sort_by": "created_at.asc"})
        for scan in scan_streamer:
            self.scans_unprocessed.append(scan["id"])

    def scan_enricher(self):
        """Enrich scans by id from queue."""
        ids_to_process = []
        while True:
            while (len(self.scans_unprocessed) > 0 and
                   len(ids_to_process) < self.batch_size):
                ids_to_process.append(self.scans_unprocessed.popleft())
            self.completed_scans.extend(self.get_details_from_batch(ids_to_process))  # NOQA
            ids_to_process = []
            time.sleep(1)

    def performance_reporter(self):
        """Periodically print out performance information."""
        time.sleep(10)
        while True:
            perf = ("Performance %s:\n\tTotal processed: %d\n\tAwaiting enrichment: %s\n\tCurrently enriching: %d\n\tOutbound: %s" %  # NOQA
                    (Utility.iso8601_now(),
                     int(self.scans_processed), len(self.scans_unprocessed),
                     int(self.currently_enriching), len(self.completed_scans)))
            if self.report_performance:
                print(perf)
            time.sleep(60)

    def get_details_from_batch(self, id_list):
        """Gets detailed scan information from batch of scans."""
        self.currently_enriching = len(id_list)
        enricher = HaloScanDetails(self.halo_key, self.halo_secret,
                                   api_host=self.api_host,
                                   api_port=self.api_port)
        enricher.set_halo_session()
        pool = ThreadPool(self.max_threads)
        results = pool.map(enricher.get, id_list)
        pool.close()
        pool.join()
        self.currently_enriching = 0
        retval = Utility.order_items(results, "created_at")
        return retval

    def set_attrs_from_kwargs(self, kwargs):
        arg_list = ["max_threads", "batch_size", "report_performance",
                    "search_params", "api_host", "api_port"]
        for arg in arg_list:
            if arg in kwargs:
                setattr(self, arg, kwargs[arg])
        if "integration_name" in kwargs:
            setattr(self, "ua", Utility.build_ua(kwargs["integration_name"]))
