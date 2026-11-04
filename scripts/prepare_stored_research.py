"""STK-083: derive an inactive INFY-only view/schedule from existing verified configs.

No database connection, provider calls, launchd activation or grant changes.
"""
import argparse,json,os
from pathlib import Path
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.scheduling import ScheduleConfig
from stock_discovery_analysis.daily_insight import LISTING,ACQUISITION
from stock_discovery_contracts.v2 import check,digest


def prepare(view,schedule,*,code_version,starts_on):
    check(LISTING in view.listing_ids,'infy_not_in_existing_view')
    check(schedule.mode=='live_paper','observed_schedule_required')
    view=view.model_copy(update={'listing_ids':(LISTING,),'pilot_scope_id':'STK-083-INFY-stored',
        'pilot_health_file':None,'descriptive_freshness_policy':'one_trailing_session_v1'})
    raw=schedule.model_dump()
    raw.update(schedule_id='STK-083-INFY-stored',scope_id=view.pilot_scope_id,
        input_hash=digest(view.model_dump(mode='json')),code_version=code_version,horizons=('swing',),starts_on=starts_on)
    return view,ScheduleConfig.model_validate(raw)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('view','schedule','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--code-version',required=True);p.add_argument('--starts-on',required=True)
    a=p.parse_args()
    view,schedule=prepare(ViewConfig.model_validate_json(a.view.read_text()),ScheduleConfig.model_validate_json(a.schedule.read_text()),code_version=a.code_version,starts_on=a.starts_on)
    a.output.mkdir(mode=0o700,exist_ok=False)
    for name,obj in [('view.json',view.model_dump(mode='json')),('schedule.json',schedule.model_dump(mode='json')),('activation.json',{'state':'inactive','acquisition':ACQUISITION,'model_execution':'disabled','calendar_through':schedule.calendar.ends_on})]:
        path=a.output/name
        with path.open('x') as f:os.chmod(path,0o600);json.dump(obj,f,indent=2)
    print('Prepared inactive stored-evidence research; verify calendar coverage before starting the existing worker.')

if __name__=='__main__':main()
