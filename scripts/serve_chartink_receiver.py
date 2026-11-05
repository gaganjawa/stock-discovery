"""STK-094 local receiver launcher with credential-bearing access logs disabled."""
import os
import uvicorn


if __name__=='__main__':
    if os.environ.get('CHARTINK_RECEIVER_ENABLED')!='true':
        raise SystemExit('Receiver disabled. Explicit simulation or future activation authorization is required.')
    # Public TLS/reverse-proxy deployment requires separate owner authorization.
    uvicorn.run('app.chartink_receiver:app',host='127.0.0.1',port=8098,
                access_log=False,limit_concurrency=20,timeout_keep_alive=5)
