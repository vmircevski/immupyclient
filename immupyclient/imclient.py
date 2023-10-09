# immudb Vault client module

from typing import Dict, Optional, List
import os

from immupyclient.helpers import aio_request, query_parser
from immupyclient.models import DocumentSearchResponse


class IMClient:
    def __init__(self, ledger_name: str = "default", collection_name: str = "default"):
        self.ledger_name = ledger_name
        self.collection_name = collection_name
        self.transactionId = None  # var to keep latest transactionId
        self.api_key = os.environ.get("VAULT_API_KEY")
        self.VAULT_PREFIX_URL = os.environ.get(
            "VAULT_PREFIX_URL", "https://vault.immudb.io/ics/api/v1/ledger/"
        )
        self.url = f"{self.VAULT_PREFIX_URL}{self.ledger_name}/collection/{self.collection_name}"
        self.url_ledger = f"{self.VAULT_PREFIX_URL}{self.ledger_name}"

    async def call(self, url: str, method: str = "get", payload: Optional[Dict] = None):
        # TODO: check if exceptions is thrown i.e. non valid api key etc..
        headers = {"X-API-Key": self.api_key, "accept": "application/json"}
        resp = await aio_request(url, method, headers, payload)
        return resp

    async def collections(self) -> Optional[List["Collection"]]:
        """list collections"""
        url = f"{self.url_ledger}/collections"
        resp = await self.call(url)
        collections_list = []
        for col_dict in resp["json"]["collections"]:
            collections_list.append(
                Collection.from_dict(self, collection_dict=col_dict)
            )
        return collections_list

    def collection(self, collection_name: Optional[str] = None):
        """creates collection object without populating it,
        it doesn't create collection in the Vaule
        """
        collection_name = collection_name or self.collection_name
        return Collection(imclient=self, collection_name=collection_name)

    def document(self, document_dict: Optional[Dict] = None):
        # Initialize document and do not create it in the Vault
        return Document(imclient=self, document_dict=document_dict)

    async def document_create_multi(
        self, document_list: List[Dict]
    ) -> Optional[List["Document"]]:
        # Initialize documents and creates them in the Vault
        documents = await Document.create_multi(
            imclient=self, document_list=document_list
        )
        return documents

    async def document_search(self, query: Optional[str]) -> Optional[List["Document"]]:
        documents = await Document.search(imclient=self, query=query)
        return documents

    async def document_replace(self, query: Optional[str], document_dict: Dict) -> Dict:
        # replaces queried documents with the content from document_dict
        documents = await Document.replace(
            imclient=self, query=query, document_dict=document_dict
        )
        return documents

    async def document_count(self, query: Optional[str]) -> int:
        count = await Document.count(imclient=self, query=query)
        return count

    async def document_audit(self, documentId: str) -> List['Document']:
        documents = await Document._audit(imclient=self, documentId=documentId)
        return documents

    async def document_proof(self, documentId: str, transactionId: int) -> Optional[Dict]:
        proof = await Document._proof(imclient=self, documentId=documentId, transactionId=transactionId)
        return proof


class Collection:
    def __init__(self, imclient: IMClient, collection_name: str):
        self.imclient = imclient
        self.collection_name = collection_name
        self.name = collection_name
        self.fields = None
        self.idFieldName = None
        self.indexes = None
        self.attributes_populated = False
        self.is_deleted = False

    @classmethod
    def from_dict(cls, imclient: IMClient, collection_dict: Dict):
        imclient = imclient
        collection_name = collection_dict["name"]
        obj = cls(imclient, collection_name)

        obj.fields = collection_dict["fields"]
        obj.idFieldName = collection_dict["idFieldName"]
        obj.indexes = collection_dict["indexes"]
        obj.name = collection_dict["name"]
        obj.attributes_populated = True
        return obj

    def __repr__(self):
        return f"Collection: '{self.collection_name}'"

    async def info(self):
        """fetch collection info"""
        url = f"{self.imclient.url_ledger}/collection/{self.collection_name}"
        resp = await self.imclient.call(url)
        resp_json = resp["json"]
        self.fields = resp_json["fields"]
        self.idFieldName = resp_json["idFieldName"]
        self.indexes = resp_json["indexes"]
        self.attributes_populated = True

    async def delete(self):
        """delete collection"""
        url = f"{self.imclient.url_ledger}/collection/{self.collection_name}"
        resp = await self.imclient.call(url, "delete")
        if resp["status"] == 200:
            self.is_deleted = True
            return True
        return False


class Document:
    def __init__(
        self,
        imclient: IMClient,
        document_dict: Optional[Dict] = None,
        documentId: Optional[str] = None,
        revision: Optional[str] = None,
        transactionId: Optional[str] = None,
        is_created: bool = False,
    ):
        """Initialize document and doesn't create it in the Vault"""
        self.imclient = imclient
        self.document_dict = document_dict
        # documentId in the Vault
        docId = None
        if documentId is not None:
            docId = documentId
        elif document_dict is not None:
            docId = document_dict.get("_id", None)
        self.documentId = docId
        self.revision = revision
        self.transactionId = transactionId
        self.is_created = is_created
        self.is_deleted = False

    async def create(self, document_dict: Optional[Dict] = None):
        # Creates document in vault from already defined document object
        doc = await self._create_in_vault(self.imclient, self.document_dict, self)
        return doc

    @classmethod
    async def create_from_dict(
        cls, imclient: IMClient, document_dict: Dict = None
    ) -> "Document":
        # Creates document in the Vault
        doc = Document(imclient, document_dict)
        doc = await cls._create_in_vault(imclient, document_dict, doc)
        return doc

    @staticmethod
    async def _create_in_vault(
        imclient: IMClient, document_dict: Optional[Dict], doc: "Document"
    ) -> "Document":
        # Creates document in the Vault
        url = f"{imclient.url}/document"
        resp = await imclient.call(url, "put", payload=document_dict)
        if resp["status"] == 200:
            doc.documentId = resp["json"]["documentId"]
            doc.transactionId = resp["json"]["transactionId"]
            doc.imclient.transactionId = resp["json"]["transactionId"]
            doc.is_created = True
        else:
            doc.is_created = False
        return doc

    @classmethod
    async def create_multi(
        cls, imclient: IMClient, document_list: List[Dict]
    ) -> Optional[List]:
        # Creates documents in the Vault
        url = f"{imclient.url}/documents"
        resp = await imclient.call(url, "put", payload={"documents": document_list})
        document_obj_list = []
        if resp["status"] == 200:
            for i in range(len(document_list)):
                document_item = document_list[i]
                documentId = resp["json"]["documentIds"][i]
                document = cls(
                    imclient, document_item, documentId=documentId, is_created=True
                )
                document_obj_list.append(document)

            imclient.transactionId = resp["json"]["transactionId"]
            return document_obj_list
        return None

    @classmethod
    async def search(
        cls,
        imclient: IMClient,
        query: Optional[str],
        page: Optional[int] = 1,
        perPage: Optional[int] = 10,
        order_by_field: Optional[str] = None,
        desc: Optional[bool] = True,
    ) -> List['Document']:
        """Searches for documents in the Vault.
        Only one order column for now.
        """
        url = f"{imclient.url}/documents/search"
        payload = {
            "query": {"expressions": [{"fieldComparisons": query_parser(query)}]},
            "page": page,
            "perPage": perPage,
        }
        if order_by_field is not None:
            payload["query"]["orderBy"] = {[[order_by_field, desc]]}

        resp = await imclient.call(url, "post", payload=payload)
        # Validate response
        DocumentSearchResponse(**resp["json"])
        document_obj_list = []
        if resp["status"] == 200:
            revisions = resp["json"]["revisions"]
            for rev in revisions:
                document = cls(
                    imclient,
                    rev["document"],
                    revision=rev["revision"],
                    is_created=True,
                )
                document_obj_list.append(document)
            return document_obj_list
        return document_obj_list

    @classmethod
    async def replace(
        cls, imclient: IMClient, query: Optional[str], document_dict: Dict
    ) -> Dict:
        url = f"{imclient.url}/document"
        payload = {
            "document": document_dict,
            "query": {"expressions": [{"fieldComparisons": query_parser(query)}]},
        }
        resp = await imclient.call(url, "post", payload=payload)
        # resp is like: {"documentId":"64bfc68e0000000000000032db10e84a","revision":"4","transactionId":"57"}
        return resp

    @staticmethod
    async def count(
        imclient: IMClient,
        query: Optional[str],
    ) -> int:
        # Counts filtered documents in the Vault.
        url = f"{imclient.url}/documents/count"
        payload = {
            "query": {"expressions": [{"fieldComparisons": query_parser(query)}]},
        }
        resp = await imclient.call(url, "post", payload=payload)
        if resp["status"] == 200:
            count = resp["json"]["count"]
            return count
        return 0

    async def audit(self):
        documents = await Document._audit(self.imclient, self.documentId)
        return documents

    @classmethod
    async def _audit(
        cls,
        imclient: IMClient,
        documentId: str,
    ) -> List['Document']:
        # Returns list of documents with transactionId and revision number
        url = f"{imclient.url}/document/{documentId}/audit"
        payload = {"desc": True, "page": 1, "perPage": 100}
        resp = await imclient.call(url, "post", payload=payload)
        document_obj_list = []
        if resp["status"] == 200:
            revisions = resp["json"]["revisions"]
            for rev in revisions:
                document = cls(
                    imclient,
                    rev["document"],
                    revision=rev["revision"],
                    transactionId=rev["transactionId"],
                    is_created=True,
                )
                document_obj_list.append(document)
        return document_obj_list

    @staticmethod
    async def _proof(
        imclient: IMClient,
        documentId: str,
        transactionId: int,
    ) -> Optional[Dict]:
        # Returns proof of a document for a specified transactionId
        # TODO: proofSinceTransactionId should be added for completeness
        url = f"{imclient.url}/document/{documentId}/proof"
        payload = {"transactionId": int(transactionId)}
        resp = await imclient.call(url, "post", payload=payload)
        proof = None
        if resp["status"] == 200:
            proof = resp["json"]
        return proof

    def __repr__(self):
        if self.revision:
            return f"Document (rev: {self.revision}): {str(self.document_dict)}"
        return f"Document: {str(self.document_dict)}"
