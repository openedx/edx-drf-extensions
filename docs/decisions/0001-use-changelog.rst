1. Use CHANGELOG.rst
====================

Status
------

Accepted

Context
-------

This repository was using Github Releases only to capture changelog details, which has the following issues:

* Additions and updates to the changelog don't go through PR review.
* The changelog is not versioned with the repository, is not available with the repo documentation, cannot be seen in a single file, and is not available offline.

Additionally, there was no guidance for formatting entries.

Decision
--------

* Add a CHANGELOG.rst as the primary source of tracking changes.
* The changelog will be formatted according to `keepachangelog.com`_.
* Avoid redundancy in Github Releases.

This resolves all issues noted under this ADR's `Context`_.

Commit Message vs Changelog Entry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since changelog messages are for developers and consumers of your code, good changelog messages will often not match commit messages. Here are some examples:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Commit Message
     - Changelog Entry
   * - deps: update dependency some-dependency to 2.3.0
     - No functional change

       Note: This example changelog entry assumes there were no other changes for this version.
   * - Fix SyntaxError in UserLogout class
     - Fix 500 error during logout
   * - Rename dry_run parameter
     - **BREAKING CHANGE** Remove the dry_run parameter in the public foobarize API method. This parameter is deprecated in favour of the no_apply parameter. See docs for details.
   * - Add set_foobarizer method to api.Foo
     - Add a set_foobarizer method to Foo's public API. This is particularly useful for developers trying to foobarize their users. See docs for details.

Consequences
------------

Regarding the discontinuation of using Github Releases:

* Writing the changelog entry in the CHANGELOG.rst should be as simple as it was to write it in Github Releases, so there should be no additional work.
* The README.rst should be updated regarding the proper way to release to avoid Github Release redundancy.
* Older Github Release messages could one day be relocated to the CHANGELOG.rst.  For now, the latest release message should clarify the change in policy and point to the CHANELOG.rst.

Additional tools:

* A Pull Request template will be added to provide a reminder.

References
----------

* `keepachangelog.com`_
* `OEP-47: Semantic Versioning`_ (Coming Soon)

.. _keepachangelog.com: https://keepachangelog.com/en/1.0.0/
.. _`OEP-47: Semantic Versioning`: https://open-edx-proposals.readthedocs.io/en/latest/oep-0047-bp-semantic-versioning.rst
