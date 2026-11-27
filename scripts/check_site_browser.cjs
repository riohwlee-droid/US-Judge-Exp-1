// Public-site browser smoke. No secrets or simulated case mutations.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const SITE="https://riohwlee-droid.github.io/US-Judge-Exp-1/";
(async()=>{
  const browser=await chromium.launch({channel:"chrome",headless:true,args:["--no-sandbox"]});
  try{
    const page=await browser.newPage({viewport:{width:390,height:844}});
    const errors=[];
    page.on("pageerror",e=>errors.push(String(e)));
    const response=await page.goto(SITE,{waitUntil:"domcontentloaded",timeout:45000});
    assert.equal(response.status(),200);
    await page.getByRole("heading",{name:"U.S. Court of Appeals for the Ninth Circuit"}).waitFor({timeout:30000});
    await page.waitForFunction(()=>document.getElementById("status").textContent.startsWith("Revision "),{},{timeout:45000});
    assert.match(await page.locator("#content").innerText(),/CA9|Ninth Circuit/);
    const first=await page.locator("#status").innerText();
    for(const tab of ["Cases","Opinions","Deadlines","Tasks","Precedents","Directory","Dashboard"]){
      await page.getByRole("button",{name:tab,exact:true}).click();
      assert.equal(await page.locator("#heading").innerText(),tab);
      if(tab==="Directory"){await page.getByText("Eleanor M. Whitaker",{exact:false}).first().waitFor({timeout:15000});}
    }
    await page.getByRole("button",{name:"Refresh",exact:true}).click();
    await page.waitForFunction(()=>document.getElementById("status").textContent.startsWith("Revision "),{},{timeout:45000});
    assert.match(await page.locator("#status").innerText(),/^Revision /);
    assert.deepEqual(errors,[]);
    await page.screenshot({path:"ca9-public-mobile.png",fullPage:true});
    await page.setViewportSize({width:1280,height:800});
    await page.screenshot({path:"ca9-public-desktop.png",fullPage:true});
    console.log("PASS: public browser navigation, official checkpoint load, refresh, and mobile/desktop rendering:",first);
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
