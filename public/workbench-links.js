// Existing public routes remain static; published content has dedicated live views.
for(const nav of document.querySelectorAll('header nav')){
  for(const [href,label] of [['/portfolio/','Portfolio'],['/blog/','Blog'],['/app/','Workbench']]){
    const a=document.createElement('a');a.href=href;a.textContent=label;nav.append(a);
  }
}
for(const button of document.querySelectorAll('.run-cell,.run-all')){
  button.replaceWith(Object.assign(document.createElement('a'),{href:'/app/notebooks?week='+String(button.dataset.week).padStart(2,'0'),textContent:'Open authenticated Notebook / 登录运行'}));
}
