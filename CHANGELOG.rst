Changelog
=========

v0.16 (2018-02-28)
------------------

Changes
~~~~~~~

- Refactor generator to use multiple threads and FIFO buffers for better
  performance. [Ash Wilson]

- Increased FIM enrichment threads from 2 to 4. Capped wait time for
  incomplete scans at 6 minutes. [Ash Wilson]

v0.15 (2018-02-25)
------------------

Changes
~~~~~~~

- Only yield scans once they've completed and can be enriched. [Ash
  Wilson]

v0.12 (2017-11-28)
------------------

- Tuned down the thread. [mong2]

v0.11 (2016-12-22)
------------------

Fix
~~~

- Fixed bad syntax in query options. [Ash Wilson]

v0.10 (2016-12-22)
------------------

Fix
~~~

- Defaults to ascending order for scan query. [Ash Wilson]

v0.9 (2016-12-20)
-----------------

New
~~~

- Retrieves and enriches scans from the Halo API. [Ash Wilson]


