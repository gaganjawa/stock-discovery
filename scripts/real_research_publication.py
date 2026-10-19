"""Explicit, rights-gated D3-09 publication and D3-10 shadow observation pass."""
import argparse
import json
from pathlib import Path
import psycopg
from stock_discovery_analysis.runtime import setting
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.real_access import source_access
from stock_discovery_analysis.real_publication import publish
from stock_discovery_analysis.shadow_tracking import pending


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    actions=parser.add_subparsers(dest='action',required=True)
    publication=actions.add_parser('publish')
    publication.add_argument('--listing',required=True)
    publication.add_argument('--horizon',choices=('swing','short_term','long_term'),required=True)
    publication.add_argument('--key',required=True)
    actions.add_parser('observe')
    args=parser.parse_args()
    config=ViewConfig.model_validate_json(args.config.read_text())
    with psycopg.connect(setting('DATABASE_URL'),autocommit=True) as conn:
        if args.action=='publish':
            artifact=publish(conn,config,args.listing,args.horizon,args.key,setting('CODE_VERSION'))
            result={'recommendation_id':artifact['recommendation']['recommendation_id'],'status':'published_shadow','actionable':False}
        else:
            result={'observations':pending(conn,source_access(config.sources)),'actionable':False}
    print(json.dumps(result))

if __name__=='__main__':main()
