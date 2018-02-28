import cloudpassage
from multiprocessing.dummy import Pool as ThreadPool


class HaloGeneral(object):
    """General Halo utilities."""
    @classmethod
    def build_halo_session(cls, halo_key, halo_secret, api_host,
                           api_port, ua):
        """Instantiates the Halo session"""
        halo_session = cloudpassage.HaloSession(halo_key, halo_secret,
                                                api_host=api_host,
                                                api_port=api_port,
                                                integration_string=ua)
        halo_session.authenticate_client()
        return halo_session

    @classmethod
    def get_pages(cls, halo_key, halo_secret, api_host, api_port, ua,
                  max_threads, url_list):
        """We map pages to threads, return results when it's all done."""
        halo_session = cls.build_halo_session(halo_key, halo_secret, api_host,
                                              api_port, ua)
        page_helper = cloudpassage.HttpHelper(halo_session)
        pool = ThreadPool(max_threads)
        results = pool.map(page_helper.get, url_list)
        pool.close()
        pool.join()
        return results
