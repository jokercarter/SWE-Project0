import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import {api,client,details,useT,ErrorText} from './core';
export function DocumentRelations({documentId}:{documentId:string}){
 const t=useT(),[course,setCourse]=useState(''),[recordId,setRecordId]=useState(''),[error,setError]=useState('');
 const links=useQuery({queryKey:['links'],queryFn:()=>api('resources/links')});
 const records=useQuery({queryKey:['link-options'],queryFn:async()=>[...await api('resources/notes'),...await api('resources/projects')]});
 return <section><form className="inline-form" onSubmit={async e=>{e.preventDefault();if(!course&&!recordId)return;try{await api('resources/links','POST',{title:documentId,status:'draft',body:JSON.stringify({course,recordId})});await client.invalidateQueries({queryKey:['links']});setCourse('');setRecordId('');}catch(e){setError(String(e));}}}><label>{t('course')}<select value={course} onChange={e=>setCourse(e.target.value)}><option value="">—</option>{Array.from({length:12},(_,i)=><option key={i} value={String(i+1).padStart(2,'0')}>Week {i+1}</option>)}</select></label><label>{t('link')}<select value={recordId} onChange={e=>setRecordId(e.target.value)}><option value="">—</option>{records.data?.map((r:any)=><option key={r.id} value={r.id}>{t(r.kind)} / {r.title}</option>)}</select></label><button>{t('save')}</button></form><ErrorText error={error}/>{links.data?.filter((r:any)=>r.title===documentId).map((r:any)=>{const d=details(r),record=records.data?.find((x:any)=>x.id===d.recordId);return <div className="toolbar" key={r.id}>{d.course&&<Link to="/app/courses">Week {d.course}</Link>}{record&&<Link to={'/app/'+record.kind+'?q='+encodeURIComponent(record.title)}>{record.title}</Link>}<button className="secondary" onClick={async()=>{try{await api('resources/links/'+r.id,'DELETE');client.invalidateQueries({queryKey:['links']});}catch(e){setError(String(e));}}}>{t('delete')}</button></div>;})}</section>;
}
export function LinkedDocuments({course,recordId}:{course?:string,recordId?:string}){
 const t=useT();const links=useQuery({queryKey:['links'],queryFn:()=>api('resources/links')}),documents=useQuery({queryKey:['documents'],queryFn:()=>api('documents')});
 const related=links.data?.filter((r:any)=>{const d=details(r);return course?d.course===course:d.recordId===recordId;})||[];
 return related.length?<div className="toolbar"><small>{t('documents')}</small>{related.map((r:any)=><Link key={r.id} to={'/app/documents?id='+r.title}>{documents.data?.find((d:any)=>d.id===r.title)?.name||r.title}</Link>)}</div>:null;
}
