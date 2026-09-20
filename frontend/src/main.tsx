import React,{useEffect,useState,lazy,Suspense} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter,Link,useLocation} from 'react-router-dom';
import {QueryClientProvider,useQuery} from '@tanstack/react-query';
import {api,client,setCsrf,Language,useT,ErrorText} from './core';
import {Dashboard,Courses,Records,Documents,Settings} from './screens';
import './style.css';
const Notebook=lazy(()=>import('./notebook'));
const Assistant=lazy(()=>import('./assistant'));
const Portfolio=lazy(()=>import('./public'));
const sections=['dashboard','courses','tasks','notes','notebooks','documents','ai','applications','projects','articles','materials','profile','settings'];
function App(){const [lang,setLang]=useState<'zh'|'en'>(localStorage.getItem('jokercarter.language')==='en'?'en':'zh');if(!location.pathname.startsWith('/app'))return <Suspense fallback={<p>Loading…</p>}><Portfolio/></Suspense>;return <Language.Provider value={lang}><Workspace lang={lang} toggle={()=>{const next=lang==='zh'?'en':'zh';setLang(next);localStorage.setItem('jokercarter.language',next);}}/></Language.Provider>;}
function Workspace({lang,toggle}:{lang:string,toggle:()=>void}){
 const t=useT(),location=useLocation();const section=location.pathname.split('/')[2]||'dashboard';
 const [error,setError]=useState(''),[theme,setTheme]=useState(localStorage.getItem('wb-theme')||'light');
 const auth=useQuery({queryKey:['auth'],queryFn:async()=>{const result=await api('auth/me');setCsrf(result.csrf);return result;}});
 const setup=useQuery({queryKey:['setup'],queryFn:()=>api('auth/status')});
 useEffect(()=>{document.documentElement.lang=lang;document.documentElement.dataset.theme=theme;},[lang,theme]);
 async function login(event:React.FormEvent<HTMLFormElement>){event.preventDefault();const data=Object.fromEntries(new FormData(event.currentTarget));try{if(setup.data?.setupRequired)await api('auth/setup','POST',data);const result=await api('auth/login','POST',data);setCsrf(result.csrf);await client.invalidateQueries();setError('');}catch(e){setError(String(e));}}
 const controls=<><button onClick={toggle}>{lang==='zh'?'English':'中文'}</button><button onClick={()=>{const next=theme==='light'?'dark':'light';setTheme(next);localStorage.setItem('wb-theme',next);}}>{t('theme')}</button></>;
 if(auth.isPending)return <p>{t('loading')}</p>;
 if(!auth.data)return <main className="login"><div className="toolbar">{controls}</div><small>JOKER CARTER / PRIVATE WORKSPACE</small><h1>{t(setup.data?.setupRequired?'setup':'welcome')}</h1><p>{t('tagline')}</p><form onSubmit={login}><label>{t('username')}<input name="username" required autoComplete="username"/></label><label>{t('password')}<input name="password" type="password" minLength={12} required autoComplete="current-password"/></label><button disabled={setup.isPending}>{t('login')}</button></form><ErrorText error={error}/><a href="/">{t('public')}</a></main>;
 return <div className="shell" data-theme={theme}><a className="skip" href="#content">Skip to content</a><aside><a href="/" className="brand">jc. <span>workbench</span></a><small>LEARN / BUILD / REFLECT</small><nav aria-label="Workspace">{sections.map(key=><Link key={key} aria-current={section===key?'page':undefined} className={section===key?'active':''} to={'/app/'+key}><span>{t(key)}</span><span aria-hidden>↗</span></Link>)}</nav>{controls}<button onClick={async()=>{await api('auth/logout','POST');client.clear();window.location.reload();}}>{t('logout')}</button></aside><main id="content" tabIndex={-1}><header><small>JOKER CARTER · LOCAL FIRST</small><h1>{t(section)}</h1><p>{t('tagline')}</p></header><Suspense fallback={<p>{t('loading')}</p>}>{section==='dashboard'?<Dashboard/>:section==='courses'?<Courses/>:section==='notebooks'?<Notebook key={location.search}/>:section==='documents'?<Documents/>:section==='ai'?<Assistant/>:section==='settings'?<Settings/>:sections.includes(section)?<Records kind={section==='materials'?'courses':section} key={section}/>:<p>404</p>}</Suspense></main></div>;
}
class Boundary extends React.Component<{children:React.ReactNode},{error:string}>{state={error:''};static getDerivedStateFromError(e:Error){return {error:e.message};}render(){return this.state.error?<main className="login"><h1>Something went wrong</h1><p>{this.state.error}</p><button onClick={()=>window.location.reload()}>Reload</button></main>:this.props.children;}}
createRoot(document.getElementById('root')!).render(<Boundary><QueryClientProvider client={client}><BrowserRouter><App/></BrowserRouter></QueryClientProvider></Boundary>);
