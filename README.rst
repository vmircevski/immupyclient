==========================================
immupyclient - immudb Vault asyncio client
==========================================

Asyncio python client for immudb Vault service. Eases using of the immudb Vault REST API and will hide most of the detail of using it directly. Tested with python 3.10

It is created to be as pythonic as possible and return obects with exception of some longer JSON responses which are returned directly as dictionaries.

It uses IMClient object to interact with immudb Vault.

* Free software: MIT license
* Documentation: https://github.com/vmircevski/immupyclient


Features
--------

* compatibility with v1 `immudb Vault API`_
* documents API support is complete, except for 'documents diff'
* collections API supports: listing, deleting and returning information. Collection is created automatically when document is created inside a collection
* NOT SUPPORTED: audit, indexes and export

Install
-------

Virtualenv is not required but is recommended. Python version 3.10.8 was used for developing this library, however newer ones should be compatible also.

In the source directory run these commands.

``pip install -r requirements_dev.txt``

``python setup.py install``

Usage
-----

For running the examples account on https://vault.immudb.io/ is required. Personal access API key with read-write permissions should be used in the following examples.

WARNING: Please use demo account as running pytest will DELETE and recreate "default" collection. (disabled for now)

These examples run from Python REPL, preferbly IPython command line which can be installed with:

``pip install ipython``



Run:
``VAULT_API_KEY=xxxxxxxxxxxx ipython``

In ipython shell create immudb Vault client:

.. code-block:: python


                from immupyclient.imclient import IMClient
                im = IMClient(ledger_name='default', collection_name='default')
                ## list collections
                colls = await im.collections()
                # colls => [Collection: 'default']

                ## create document
                doc_dict = {'name': 'John Doe',
                            'id': 1,
                            'timestamp': '2023-05-10T12:00:00Z',
                            'email': 'johndoe@example.com',
                            'age': 30,
                            'address': '123 Main Street',
                            'city': 'New York',
                            'country': 'USA',
                            'phone': '+1-123-456-7890',
                            'is_active': True}
                # creates local document obj but doesn't creates in the Vault
                doc = im.document(doc_dict)
                # doc => Document: {'name': 'John Doe', 'id': 1, 'timestamp': '2023-05-10T12:00:00Z', 'email': 'johndoe@example.com', 'age': 30, 'address': '123 Main Street', 'city': 'New York', 'country': 'USA', 'phone': '+1-123-456-7890', 'is_active': True}
                # doc.is_created == False

                # create same document in the Vault
                await doc.create()
                # doc.transactionId will be populated

                ## search for documents in the Vault
                # query formatting is same as the one in the Search Bar on the immudb Vault web app.
                query = "name='John Doe'"
                docs = await im.document_search(query)
                # docs => List of Document

                ## replace document
                replace_dict = {'name': 'Will Smith',
                                'id': 2,
                                'timestamp': '2023-05-10T12:00:00Z',
                                'email': 'willsmith@example.com',
                                'age': 30,
                                'address': '123 Main Street',
                                'city': 'New York',
                                'country': 'USA',
                                'phone': '+1-123-456-7890',
                                'is_active': True}

                replaced_docs = await im.document_replace(query, replace_dict)
                # replaced_docs is JSON response from the Vault server
                # if there is no documents for replacing VaultResponseException is raised with
                # status: 404 and description of the error from server

                ## create multiple documents
                docs = await im.document_create_multi([doc_dict, replace_dict])
                # docs => list of created Document objects

                ## count queried documents
                cnt = await im.document_count(query)
                # ex. cnt: integer => 1, count of filtered documents

                ## audit items for provided document
                revs = await doc.audit()
                # revs => list of Document objects with populated 'transactionId' and 'revision' attributes






Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`immudb Vault API`: https://vault.immudb.io/docs/api/v1
