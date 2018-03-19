import cloudpassage
import datetime
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
        self.init_time = datetime.datetime.now()
        self.api_port = 443
        self.max_threads = 10
        self.batch_size = 30
        self.scans_by_module = {}
        self.last_scan_timestamp = None
        self.currently_enriching = 0
        self.scans_processed = 0
        self.scans_unprocessed = deque([])
        self.completed_scans = deque([])
        self.report_performance = False
        self.halo_session = None
        self.ua = Utility.build_ua("")
        self.scan_timeout = 300
        self.shutdown = False
        self.search_params = {}  # Set params empty
        self.search_params["since"] = Utility.iso8601_now()  # Default to 'now'
        self.kwargs = kwargs
        self.set_attrs_from_kwargs(kwargs)
        if "start_timestamp" in kwargs:  # Final authority on start time.
            self.search_params["since"] = kwargs["start_timestamp"]
        self.search_params["sort_by"] = "created_at.asc"  # Force sort
        print("Search params: %s" % self.search_params)

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
        self.shutdown = False
        # We configure the ingestion thread
        self.ingest = threading.Thread(target=self.scan_id_preloader)
        self.ingest.daemon = True
        # Next, we configure the enrichment thread.
        self.enrich = threading.Thread(target=self.scan_enricher)
        self.enrich.daemon = True
        # Next, we configure the performance reporter thread.
        self.performance = threading.Thread(target=self.performance_reporter)
        self.performance.daemon = True
        # Starting threads
        self.ingest.start()
        self.enrich.start()
        self.performance.start()
        while True:
            healthy = True
            if self.shutdown is True:  # This is how we cleanly shutdown.
                print("Stopping threads...")
                self.ingest.join(20)
                self.enrich.join(20)
                self.performance.join(60)
                self.ingest = None
                self.enrich = None
                self.performance = None
                self.shutdown = False  # Reset, in case we want to re-start
                raise StopIteration
            elif not self.ingest.is_alive():
                healthy = False
                print("Ingestion thread has died!")
            elif not self.enrich.is_alive():
                healthy = False
                print("Enrichment thread has died!")
            elif not self.performance.is_alive():
                healthy = False
                print("Performance monitoring thread has died!")
            if not healthy:  # Gracefully shutdown if unhealthy.
                print("Timestamp from last scan processed: %s" %
                      self.last_scan_timestamp)
                self.shutdown = True
                continue
            # Now, we yield a scan if any are waiting.
            try:
                current_scan = self.completed_scans.popleft()
                self.last_scan_timestamp = current_scan["created_at"]
                self.scans_processed += 1
                self.tally_scan(str(current_scan["module"]))
                yield current_scan
            except IndexError:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    self.shutdown = True
            except KeyboardInterrupt:
                self.shutdown = True

    def scan_id_preloader(self):
        """Get scan metadata from /v1/scans endpoint, load ids into queue."""
        scan_streamer = cloudpassage.TimeSeries(self.halo_session,
                                                self.search_params["since"],
                                                "/v1/scans", "scans",
                                                self.search_params)
        for scan in scan_streamer:
            if self.shutdown:
                break
            self.scans_unprocessed.append(scan["id"])
        print("Stopped scan ID preloader thread.")
        return

    def scan_enricher(self):
        """Enrich scans by id from queue."""
        ids_to_process = []
        while True:
            if self.shutdown:
                break
            while (len(self.scans_unprocessed) > 0 and
                   len(ids_to_process) < self.batch_size):
                ids_to_process.append(self.scans_unprocessed.popleft())
            self.completed_scans.extend(self.get_details_from_batch(ids_to_process))  # NOQA
            ids_to_process = []
            time.sleep(1)
        print("Stopped scan enricher thread.")
        return

    def performance_reporter(self):
        """Periodically print out performance information."""
        time.sleep(10)
        while True:
            if self.shutdown:
                break
            uptime = int((datetime.datetime.now() - self.init_time).seconds)
            scans_per_second = str(self.scans_processed / uptime)
            perf = "Performance %s:\n" % Utility.iso8601_now()
            perf += "\tRunning for %s seconds\n" % uptime
            perf += "\tTotal processed: %d\n" % int(self.scans_processed)
            perf += "\tBy module:\n\t\t%s\n" % self.get_scan_counts_by_module()
            perf += "\tScans per second: %s\n" % scans_per_second
            perf += "\tAwaiting enrichment: %s\n" % len(self.scans_unprocessed)
            perf += "\tEnriching now: %d\n" % int(self.currently_enriching)
            perf += "\tOutbound: %s\n" % len(self.completed_scans)
            if self.report_performance:
                print(perf)
            time.sleep(60)
        print("Stopped performance reporter thread.")
        return

    def get_details_from_batch(self, id_list):
        """Gets detailed scan information from batch of scans."""
        self.currently_enriching = len(id_list)
        enricher = HaloScanDetails(self.halo_key, self.halo_secret,
                                   api_host=self.api_host,
                                   api_port=self.api_port,
                                   scan_timeout=self.scan_timeout)
        enricher.set_halo_session()
        pool = ThreadPool(self.max_threads)
        results = pool.map(enricher.get, id_list)
        pool.close()
        pool.join()
        self.currently_enriching = 0
        retval = Utility.order_items(results, "created_at")
        return retval

    def get_scan_counts_by_module(self):
        ret_lst = []
        for module, count in sorted(self.scans_by_module.items()):
            ret_lst.append("%s: %s" % (module, count))
        return " | ".join(ret_lst)

    def tally_scan(self, scan_module):
        if scan_module not in self.scans_by_module:
            self.scans_by_module[scan_module] = 1
        else:
            self.scans_by_module[scan_module] += 1
        return

    def set_attrs_from_kwargs(self, kwargs):
        arg_list = ["max_threads", "batch_size", "report_performance",
                    "search_params", "api_host", "api_port", "scan_timeout"]
        for arg in arg_list:
            if arg in kwargs:
                setattr(self, arg, kwargs[arg])
        if "integration_name" in kwargs:
            setattr(self, "ua", Utility.build_ua(kwargs["integration_name"]))
