import {test,expect} from '@playwright/test';
test('private workflow, notebook state, publication, language and responsive layout',async({page,request})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/app/');
 await page.getByLabel('用户名').fill('browser-test');await page.getByLabel('密码（至少 12 位）').fill('browser-test-password-2026');
 await page.getByRole('button',{name:'进入工作台',exact:true}).click();await expect(page.getByRole('heading',{name:'概览',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'任务看板',exact:true}).click();await page.getByRole('button',{name:'创建',exact:true}).click();
 await page.getByLabel('标题',{exact:true}).fill('Build tested API');await page.getByLabel('Markdown 内容').fill('Verify **real** behavior');await page.locator('.editor').getByLabel('优先级').selectOption('high');
 await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByRole('heading',{name:'Build tested API'}).first()).toBeVisible();await page.getByRole('button',{name:'取消',exact:true}).click();
 await page.getByRole('button',{name:'看板',exact:true}).click();await page.getByLabel('状态 Build tested API').selectOption('doing');
 await page.reload();await expect(page.getByLabel('状态 Build tested API')).toHaveValue('doing');
 await page.getByRole('link',{name:'学习中心',exact:true}).click();await page.getByRole('checkbox').first().check();await page.reload();await expect(page.getByRole('checkbox').first()).toBeChecked();
 await page.getByRole('link',{name:'学习日志',exact:true}).click();await page.getByRole('button',{name:'创建',exact:true}).click();await page.getByLabel('标题',{exact:true}).fill('Learning journal');await page.getByLabel('Markdown 内容').fill('## Transaction\nAtomicity means all or nothing.');
 await expect(page.getByRole('status')).toHaveText('已保存',{timeout:10000});
 await page.getByRole('button',{name:'English',exact:true}).click();await expect(page.getByLabel('Markdown content')).toHaveValue('## Transaction\nAtomicity means all or nothing.');
 await page.getByRole('button',{name:'Cancel',exact:true}).click();await page.getByRole('link',{name:'Notebooks',exact:true}).click();await expect(page.locator('.notebook-cell')).toHaveCount(6);
 await page.getByRole('button',{name:'Run cell',exact:true}).first().click();await expect(page.getByRole('status')).toHaveText(/Saved|Execution finished/,{timeout:45000});await expect(page.locator('.outputs')).toContainText(['Task']);
 await page.getByRole('button',{name:'中文',exact:true}).click();await expect(page.locator('.outputs').first()).toContainText('Task');
 await page.getByRole('link',{name:'知识库',exact:true}).click();await expect(page.getByRole('heading',{name:'知识库',exact:true})).toBeVisible();await page.getByLabel('上传 PDF / TXT / Markdown').setInputFiles({name:'evidence.md',mimeType:'text/markdown',buffer:Buffer.from('A transaction groups changes into one atomic commit.')});await expect(page.getByRole('status')).toHaveText('索引完成');
 await page.getByRole('textbox',{name:'搜索',exact:true}).fill('transaction');await expect(page.getByText('A transaction groups changes into one atomic commit.').first()).toBeVisible();
 await page.getByLabel('关联周次').selectOption('01');await page.getByLabel('关联记录 ID').selectOption({label:'学习日志 / Learning journal'});await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByRole('link',{name:'Learning journal',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'项目管理',exact:true}).click();await page.getByRole('button',{name:'创建',exact:true}).click();await page.getByLabel('标题',{exact:true}).fill('Browser verified project');await page.getByLabel('Markdown 内容').fill('**Evidence**: browser test ran.');await page.locator('.editor').getByLabel('状态',{exact:true}).selectOption('published');await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByRole('status')).toHaveText('已保存');
 await page.goto('/portfolio/');await expect(page.getByRole('link',{name:'Browser verified project'})).toBeVisible();
 for(const path of ['/','/projects/','/about/','/learning/','/learning/code/','/projects/pathfinder/']){const r=await request.get(path);expect(r.status()).toBe(200);}
 await page.goto('/app/tasks');await page.setViewportSize({width:390,height:844});await expect(page.getByRole('heading',{name:'任务看板'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await page.screenshot({path:'output/workbench-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});await page.goto('/app/dashboard');await page.screenshot({path:'output/workbench-desktop.png',fullPage:true});expect(errors).toEqual([]);
});

