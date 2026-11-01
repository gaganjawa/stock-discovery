"""Bounded comparisons of persisted fictional research, never investment acceptance."""
import pytest
from test_publication import database,client,HEADERS,isolated_url
from stock_discovery_analysis.publication_fixtures import SOURCE


def page(client,**params):
    response=client.get('/v1/discovery',params=params,headers=HEADERS)
    assert response.status_code==200,response.text
    return response.json()


def compare(client,ids,headers=HEADERS):
    return client.get('/v1/recommendations/'+ids[0]+'/comparisons',
        params=[('compare_to',rid) for rid in ids[1:]],headers=headers)


def test_ranking_is_frozen_stable_and_paged(client,database):
    c,_,_=database
    first=page(client,limit=2)
    second=page(client,limit=3,batch_id=first['batch_id'],cursor=first['next_cursor'])
    rows=first['recommendations']+second['recommendations']
    rankings={**first['rankings'],**second['rankings']}
    assert len(rows)==len(rankings)==5
    keys=[]
    for r in rows:
        rank=rankings[r['recommendation_id']]
        frozen=c.execute('SELECT artifact FROM discovery.recommendations WHERE recommendation_id=%s',
            (r['recommendation_id'],)).fetchone()[0]
        assert rank==frozen['ranking'] and rank['ai_component']=='0'
        keys.append((rank['action_tier'],-int(rank['quant_score']),rank['listing_id']))
    assert keys==sorted(keys)
    assert page(client,limit=2,batch_id=first['batch_id'])['rankings']==first['rankings']


@pytest.mark.parametrize('count',[2,4])
def test_comparison_is_bounded_order_independent_and_read_only(client,database,count):
    c,_,_=database
    rows=page(client)['recommendations'][:count]
    ids=[r['recommendation_id'] for r in rows]
    before=c.execute("SELECT (SELECT count(*) FROM discovery.recommendations),"
        "(SELECT count(*) FROM discovery.rag_reservations),(SELECT count(*) FROM paper.ledger)").fetchone()
    response=compare(client,ids)
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    result=response.json()
    assert result==compare(client,list(reversed(ids))).json()
    assert len(result['items'])==count and result['labels']==['MOCK','SHADOW','NON-ACTIONABLE']
    for item in result['items']:
        r=item['recommendation']
        assert r['paper_admission']['status']=='blocked' and r['paper_admission']['quantity'] is None
        assert 'outcome' not in item and 'trade' not in item and item['metrics']
    assert c.execute("SELECT (SELECT count(*) FROM discovery.recommendations),"
        "(SELECT count(*) FROM discovery.rag_reservations),(SELECT count(*) FROM paper.ledger)").fetchone()==before


@pytest.mark.parametrize('other_scope',[{'horizon':'long_term'},{'cohort':'quant_rag'}])
def test_comparison_rejects_incompatible_scope(client,other_scope):
    left=page(client)['recommendations'][0]['recommendation_id']
    right=page(client,**other_scope)['recommendations'][0]['recommendation_id']
    response=compare(client,[left,right])
    assert response.status_code==400 and response.json()['detail']['code']=='comparison_scope_mismatch'
    assert 'items' not in response.json()


def test_comparison_auth_duplicates_missing_and_limits(client):
    ids=[r['recommendation_id'] for r in page(client)['recommendations']]
    assert compare(client,ids[:2],headers={}).status_code==401
    assert compare(client,[ids[0],ids[0]]).status_code==400
    assert compare(client,[ids[0],'unknown']).status_code==404
    assert compare(client,ids).status_code==422
    legacy=client.get('/v1/recommendations/'+ids[0]+'/comparisons',headers=HEADERS)
    assert legacy.status_code==200 and len(legacy.json()['recommendations'])==3


def test_comparison_rechecks_revocation_after_previous_success(client,database):
    c,_,_=database
    ids=[r['recommendation_id'] for r in page(client,cohort='quant_rag')['recommendations'][:2]]
    assert compare(client,ids).status_code==200
    with c.transaction(force_rollback=True):
        c.execute('INSERT INTO discovery.publication_source_controls VALUES (%s,true) '
            'ON CONFLICT (source_id) DO UPDATE SET revoked=true',(SOURCE,))
        response=compare(client,ids)
        assert response.status_code==403
        assert 'items' not in response.json() and 'Fictional' not in response.text


def test_comparison_rejects_different_batch_even_with_same_cutoff(client,monkeypatch):
    import app.discovery as module
    original=module.read_artifact
    ids=[r['recommendation_id'] for r in page(client)['recommendations'][:2]]
    def other_batch(c,rid):
        import copy
        artifact=copy.deepcopy(original(c,rid))
        if rid==ids[1]:artifact['recommendation']['run_id']='another-batch'
        return artifact
    monkeypatch.setattr(module,'read_artifact',other_batch)
    assert compare(client,ids).status_code==400
