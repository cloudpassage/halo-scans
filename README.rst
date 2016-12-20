Python module: haloevents
=========================

What it is:
-----------

Multi-threaded API wrapper for the CloudPassage /v1/scans endpoint.  Give it
API creds and talk to it like it's a generator.  See example, below.


Installing:
-----------

* Clone this repository down and enter its root dir
* pip install .


Example usage:
--------------

The following example retrieves a list of all scans for a day, then queries
the API to enrich the basic scan metadata with scan findings.  Finally, we
pretty-print the scan results.

::


        import haloscans
        import pprint
        scans = haloscans.HaloScans(key, secret, start_timestamp=start_timestamp)
        enricher = haloscans.HaloScanDetails(key, secret)
        enriched_scans = []
        for scan in scans:
            if not scan["created_at"].startswith(start_timestamp):
                break
            else:
                enriched_scans.append(enricher.get(scan["id"]))
        for e_scan in enriched_scans:
            message = "ID: %s\tType: %s\nFindings: %s\n\n" % (e_scan["id"], e_scan["module"], pprint.pformat(e_scan))
            print(message)



Testing:
--------

py.test --cov=haloscans
