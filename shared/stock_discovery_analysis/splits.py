"""Audit fixed synthetic session splits without reading realized outcomes."""
from .dataset import chronological_windows
from .replay import dt
from .strategy import CONFIG_VERSION, stamp


def split_report(dataset, analyses):
    sessions=dataset.calendar.sessions
    windows=chronological_windows(len(sessions),gap=5)
    names=('development','validation','test')
    result={name:{'start_at':stamp(sessions[windows[name][0]].opens_at),
                  'end_at':stamp(sessions[windows[name][1]-1].closes_at),
                  'recommendation_ids':[]} for name in names}
    excluded=[]
    for analysis in analyses:
        r=analysis['recommendation']; rid=r['recommendation_id']; cutoff=dt(r['information_cutoff_at'])
        reason=None
        index=next((i for i,s in enumerate(sessions) if s.closes_at<=cutoff and
                    (i+1==len(sessions) or cutoff<sessions[i+1].opens_at)),None)
        name=next((n for n in names if index is not None and windows[n][0]<=index<windows[n][1]),None)
        if r['versions']['dataset']!=dataset.version: reason='dataset_mismatch'
        elif r['strategy']['config_version']!=CONFIG_VERSION: reason='unsupported_label_policy'
        elif index is None: reason='cutoff_outside_closed_session'
        elif name is None: reason='boundary_gap'
        elif index+5>=len(sessions): reason='label_horizon_outside_calendar'
        else:
            # Reserve five future sessions for every action, including abstentions.
            # This is the frozen baseline's forecast/entry-validity+holding bound.
            endpoint=sessions[index+5].closes_at
            forecast=r.get('forecast')
            execution=r.get('execution')
            if forecast and dt(forecast['end_at'])>endpoint:
                reason='label_exceeds_frozen_policy'
            if execution:
                eligible=[i for i,s in enumerate(sessions) if dt(r['earliest_executable_entry_at'])<=s.opens_at<dt(execution['entry_expires_at'])]
                last=eligible[-1]+execution['max_holding_sessions']-1 if eligible else len(sessions)
                if last>=len(sessions) or sessions[last].closes_at>endpoint:
                    reason='label_exceeds_frozen_policy'
            next_name=names[names.index(name)+1] if name!='test' else None
            if next_name and endpoint>=dt(result[next_name]['start_at']): reason='label_overlaps_next_split'
        if reason: excluded.append({'id':rid,'reason':reason})
        else: result[name]['recommendation_ids'].append(rid)
    return {'policy':'SYN-60-20-20-gap5-label5-v1','calendar_version':dataset.calendar.version,
            'gap_sessions':5,'maximum_label_sessions':5,'windows':result,'exclusions':excluded,
            'status':'synthetic_audit_only',
            'limitation':'Session-based synthetic audit, not EP-1 complete-month validation or an untouched-test guarantee.'}
