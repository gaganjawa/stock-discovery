"""Private, reload-on-use source configuration shared by real worker and readers."""
import json
from pathlib import Path
from stock_discovery_contracts.rights import Grant, UseRequest
from stock_discovery_contracts.v2 import Strict, Text, check
from pydantic import Field
from typing import Annotated
from .evidence_storage import Access
from .publication_store import now

class SourceConfig(Strict):
    grant_file: Text
    region: Text = 'IN'
    retention_days: Annotated[int, Field(ge=1,le=3650)]
    primary_source_ids: tuple[Text,...] = ()

def source_access(config, clock=now, audit=lambda d:None):
    config=SourceConfig.model_validate(config)
    def load(stream):
        grants=[Grant.model_validate_json(json.dumps(g)) for g in json.loads(Path(config.grant_file).read_text())]
        matches=[g for g in grants if (g.source_id,g.account_ref)==(stream.source_id,stream.account_ref)]
        check(len(matches)<=1,'ambiguous_source_grant')
        return matches[0] if matches else None
    def request(stream):
        return UseRequest(source_id=stream.source_id,account_ref=stream.account_ref,scope=stream.scope,
            uses=('derive',),region=config.region,destination_region=None,processor_ref=None,
            requested_at=clock(),synthetic=False,units=100,retention_days=config.retention_days,attribution_present=True)
    return Access(load,request,audit,clock,frozenset(config.primary_source_ids))
