"""Launch the STK-100 operator app locally; never accept a public bind address."""
import argparse
from pathlib import Path
import os
import sys


def arguments(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8502)
    args=parser.parse_args(argv)
    if not 1024<=args.port<=65535:parser.error('port must be between 1024 and 65535')
    app=Path(__file__).resolve().parents[1]/'tools/vps_browser/app.py'
    return ['streamlit','run',str(app),'--server.address=127.0.0.1',f'--server.port={args.port}',
        '--server.headless=true','--server.enableCORS=true','--server.enableXsrfProtection=true',
        '--server.enableStaticServing=false','--server.enableAgentApi=false',
        '--server.maxUploadSize=0','--server.allowedHosts=127.0.0.1',
        '--server.fileWatcherType=none','--browser.gatherUsageStats=false']


def main():
    args=arguments()
    try:from streamlit.web import cli
    except ImportError:raise SystemExit('Install the optional locked tools/vps_browser requirements first.') from None
    os.chdir(Path(args[2]).parent)
    sys.argv=args
    return cli.main()


if __name__=='__main__':raise SystemExit(main())
