import {test,expect} from '@playwright/test';
test('notebook import/export, safe rendering, backups and keyboard',async({page})=>{
 await page.goto('/app/');
 await page.getByLabel('用户名').fill('browser-test');await page.getByLabel('密码（至少 12 位）').fill('browser-test-password-2026');await page.getByRole('button',{name:'进入工作台',exact:true}).click();await expect(page.getByRole('heading',{name:'概览',exact:true})).toBeVisible();
 const csrf=(await (await page.request.get('/api/auth/me')).json()).csrf;
 const imported={nbformat:4,nbformat_minor:5,metadata:{},cells:[{id:'first',cell_type:'code',metadata:{},source:'shared = 41',execution_count:null,outputs:[]},{id:'second',cell_type:'code',metadata:{},source:'print(shared + 1)',execution_count:null,outputs:[]}]};
 await page.goto('/app/notebooks?week=12');await expect(page.locator('.notebook-cell')).toHaveCount(6);
 await page.getByLabel('导入',{exact:true}).setInputFiles({name:'example.ipynb',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(imported))});await expect(page.locator('.notebook-cell')).toHaveCount(2);
 await page.getByRole('button',{name:'运行全部',exact:true}).click();await expect(page.locator('.outputs').last()).toContainText('42',{timeout:20000});
 await expect(page.getByRole('status')).toHaveText('已保存');await page.reload();await expect(page.locator('.outputs').last()).toContainText('42');
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'导出',exact:true}).click();const exported=await downloadPromise;expect(exported.suggestedFilename()).toBe('week-12.ipynb');
 await page.getByRole('button',{name:'上移',exact:true}).last().click();await expect(page.locator('.cm-content').first()).toContainText('print(shared + 1)');
 await page.getByRole('button',{name:'深浅主题',exact:true}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await page.screenshot({path:'output/notebook-mobile-dark.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});
 const body={title:'Safe rendering',status:'published',body:JSON.stringify({body:'<img src=x onerror="window.__wb_xss_probe=true">\n[bad](javascript:alert(1))',completion:'planned',architecture:'flowchart LR\nBrowser --> API\nAPI --> Database'})};
 const response=await page.request.post('/api/resources/projects',{headers:{'x-csrf-token':csrf},data:body});expect(response.ok()).toBeTruthy();
 const record=await response.json();await page.goto('/portfolio/'+record.id);await expect(page.locator('.architecture svg')).toBeVisible({timeout:20000});await expect(page.locator('.architecture')).toContainText('Browser');expect(await page.evaluate(()=>(window as any).__wb_xss_probe)).toBeUndefined();expect(await page.locator('a[href^="javascript:"]').count()).toBe(0);await page.screenshot({path:'output/public-project.png',fullPage:true});
 await page.goto('/app/settings');const backup=await (await page.request.get('/api/backup')).body();await page.getByLabel('预览备份恢复').setInputFiles({name:'backup.json',mimeType:'application/json',buffer:backup});await expect(page.getByRole('button',{name:'确认合并恢复'})).toBeVisible();await page.getByRole('button',{name:'确认合并恢复'}).click();await expect(page.getByRole('status')).toHaveText('已保存');
 await page.evaluate(()=>localStorage.setItem('jokercarter.learning.progress.v1',JSON.stringify({'01-0':true})));
 await page.getByRole('button',{name:'预览浏览器旧进度'}).click();await page.getByRole('button',{name:'确认导入里程碑'}).click();await expect.poll(async()=>{const r=await page.request.get('/api/resources/legacy');return (await r.json()).length;}).toBe(1);
 await page.keyboard.press('Tab');expect(await page.evaluate(()=>document.activeElement?.tagName)).not.toBe('BODY');
});


