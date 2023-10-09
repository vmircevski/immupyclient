from typing import Dict, Optional, List

from json import JSONDecodeError

import aiohttp
from aiohttp import ContentTypeError

from immupyclient.enums import SymbolType
from immupyclient.exceptions import VaultResponseException


async def aio_request(
    url: str,
    method: str = "get",
    headers: Optional[Dict] = None,
    payload: Optional[Dict] = None,
) -> Dict:
    """makes async http requests with specified method
    and expects json response
    """
    async with aiohttp.ClientSession(headers=headers) as session:
        session_request = getattr(session, method)
        async with session_request(url, json=payload, headers=headers) as r:
            try:
                print(await r.text(), r.status)
                json_body = await r.json()
            except (JSONDecodeError, ContentTypeError):
                json_body = None
            if r.status >= 400:
                raise VaultResponseException(r.status, json_body)
            return {"status": r.status, "json": json_body}


def query_parser(qry: str) -> List[Dict]:
    """Returns JSON query from search string as per immudb Vault docs.
    Search string formatting is same as immudb Vault's:
    https://vault.immudb.io/docs/guide/immudb-vault/immudb_vault_quickstart#home-page
    id=10 name=Adam ; id>=10 ; name="Joe Starr" ; name:"^Joe"
    Spaces between the expressions are not allowed for now
    """
    qry += " "  # adding space at the end in order to not go over max index
    ops = ["=", "!=", "<", "<=", ">", ">=", ":"]
    ops_str = ["EQ", "NE", "LT", "LE", "GT", "GE", "LIKE"]
    qry_list = []  # ex. ["name", "EQ", "Joe", "id", "EQ", 2]
    temp = ""  # buffer for keeping the vars,ops or values
    symbol_type = SymbolType.NAME.value  # starting with "name"
    i = 0
    inside_quotes = False
    max_i = len(qry) - 2
    while i <= max_i:
        c = qry[i]
        cc = c + qry[i + 1]
        if symbol_type == SymbolType.NAME.value:
            if c != " " and c not in ops and cc not in ops:
                temp += c
                i += 1
                continue
            elif cc in ops:
                qry_list.append(temp)
                temp = ""
                i += 2
                qry_list.append(ops_str[ops.index(cc)])
                symbol_type = SymbolType.VAL.value
                inside_quotes = False
                continue
            elif c in ops:
                qry_list.append(temp)
                temp = ""
                qry_list.append(ops_str[ops.index(c)])
                i += 1
                symbol_type = SymbolType.VAL.value
                inside_quotes = False
                continue
        if symbol_type == SymbolType.VAL.value:
            if c in ['"', "'"]:
                if inside_quotes:  # finished with parsng value
                    i += 1
                    qry_list.append(temp)
                    temp = ""
                    symbol_type = SymbolType.NAME.value
                    continue
                else:
                    inside_quotes = True
                    i += 1
                    continue
            if (not inside_quotes and c != " ") or (inside_quotes):
                temp += c
                i += 1
                if i > max_i:
                    # apend val if we are at the end
                    qry_list.append(temp)
                continue
            else:
                qry_list.append(temp)
                temp = ""
                symbol_type = SymbolType.NAME.value
                continue
        i += 1
    j = 0
    fieldComparisons = []
    while j <= len(qry_list) - 1:
        elem = {
            "field": qry_list[j],
            "operator": qry_list[j + 1],
            "value": qry_list[j + 2],
        }
        fieldComparisons.append(elem)
        j += 3
    return fieldComparisons
