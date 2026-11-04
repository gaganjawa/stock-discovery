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
    for k in ('repo','python','database'): p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    view,schedule=prepare(ViewConfig.model_validate_json(a.view.read_text()),ScheduleConfig.model_validate_json(a.schedule.read_text()),code_version=a.code_version,starts_on=a.starts_on)
    if any((a.repo,a.python,a.database)) and not all((a.repo,a.python,a.database)):
        p.error('durable preparation requires --repo, --python and --database')
    manifest=None
    if a.repo:
        from worker.stored_operations import deployment
        manifest=deployment(a.repo,a.python,a.database,view,schedule,a.output)
    write_prepared(a.output,view,schedule,manifest=manifest)
    print('Prepared inactive stored-evidence research; verify calendar coverage before starting the existing worker.')

def write_prepared(output,view,schedule,*,manifest=None):
    """Exclusive preparation: never overwrite an earlier valid deployment.

    Validate and serialize everything before creating the directory. A failed
    write leaves no valid activation manifest; no existing file is removed.
    """
    values=[('view.json',view.model_dump(mode='json')),('schedule.json',schedule.model_dump(mode='json')),
        ('activation.json',{'state':'inactive','acquisition':ACQUISITION,'model_execution':'disabled','calendar_through':schedule.calendar.ends_on})]
    if manifest: values.append(('deployment.json',manifest))
    values=[(name,json.dumps(obj,indent=2)) for name,obj in values]
    output=Path(output).absolute();output.mkdir(mode=0o700,exist_ok=False)
    for name,body in values:
        with (output/name).open('x') as f:os.chmod(output/name,0o600);f.write(body)


if __name__=='__main__':main()
