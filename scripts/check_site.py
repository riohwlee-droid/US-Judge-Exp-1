"""External HTTP smoke check of published site and raw official data; not browser execution."""
import hashlib, json, time, urllib.request
SITE="https://riohwlee-droid.github.io/US-Judge-Exp-1/"
RAW="https://raw.githubusercontent.com/riohwlee-droid/US-Judge-Exp-1/main/"
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"CA9-simulation-smoke","Cache-Control":"no-cache"}),timeout=15) as response:
        assert response.status==200
        return response.read()
def check():
    page=get(SITE)
    assert b"Ninth Circuit" in page
    assert b"chambers.js" in page
    assert b"refresh" in get(SITE+"chambers.js")
    assert get(SITE+"chambers.css")
    p=json.loads(get(RAW+"CURRENT.json"))
    m=get(RAW+"saves/"+p["checkpoint"]+"/manifest.json")
    assert hashlib.sha256(m).hexdigest()==p["manifest_sha256"]
    state=json.loads(get(RAW+json.loads(m)["state_path"]))
    assert state["revision"]==p["revision"]
    print("PASS: public site HTML/CSS/JS and remote checkpoint revision",p["revision"])
if __name__=="__main__":
    for i in range(6):
        try:
            check()
            break
        except Exception as e:
            if i==5: raise
            print("Retry:",e,flush=True)
            time.sleep(10)
