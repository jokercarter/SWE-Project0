import {useContext} from 'react';
import {useQuery} from '@tanstack/react-query';
import Markdown from './markdown';
import {api,details,Language} from './core';
export default function Materials(){const en=useContext(Language)==='en';const q=useQuery({queryKey:['public-materials'],queryFn:()=>api('public/courses')});if(!q.data?.length)return null;return <section className="panel"><h2>{en?'Published course materials':'已发布课程资料'}</h2>{q.data.map((r:any)=>{const d=details(r);return <article key={r.id}><h3>{r.title}</h3><small>Week {d.course||'—'} · {d.tags}</small><Markdown>{d.body||''}</Markdown>{/^(https?:\/\/|\/[^/])/.test(d.url||'')&&<a href={d.url} target="_blank" rel="noreferrer">{en?'Read material':'阅读资料'}</a>}</article>;})}</section>;}
