from typing import List, Dict
from pydantic import BaseModel, StrictInt, Field, ConfigDict


class DocumentCreateResponse(BaseModel):
    transactionId: StrictInt
    documentId: str


class DocumentReplaceResponse(BaseModel):
    transactionId: StrictInt
    documentId: str
    revision: StrictInt


class VaultMdSchema(BaseModel):
    creator: str
    ts: StrictInt


class DocumentSchema(BaseModel):
    model_config = ConfigDict(extra='allow')

    id: str = Field(alias="_id")
    vault_md: VaultMdSchema = Field(alias="_vault_md")

    # ConfigDict =
    #     extra = "allow"


class RevisionSchema(BaseModel):
    transactionId: str
    revision: str
    document: DocumentSchema


class DocumentSearchResponse(BaseModel):
    searchId: str
    revisions: List[RevisionSchema]
    page: StrictInt = Field(gt=0)
    perPage: StrictInt = Field(gt=0, lt=101)
