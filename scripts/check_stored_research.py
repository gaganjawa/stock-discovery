"""STK-086: private read-only readiness. No bootstrap, provider calls or DB writes."""
import argparse
import json
from worker.stored_operations import check_deployment
from activate_pilot_launchd import status, STORED_LABEL, LABEL


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deployment',required=True)
    args=parser.parse_args()
    result=check_deployment(args.deployment)
    try:
        result['launchd']=[status(label=label) for label in (STORED_LABEL,LABEL)]
    except (OSError,RuntimeError):
        result['launchd']={'status':'unverified'}
        result['status']='BLOCKED';result['recurring_activation_safe']=False
        result['reasons'].append('launchd_status_unverified')
    print(json.dumps(result,indent=2))
    return 2 if result['status']=='BLOCKED' else 0


if __name__=='__main__':raise SystemExit(main())
