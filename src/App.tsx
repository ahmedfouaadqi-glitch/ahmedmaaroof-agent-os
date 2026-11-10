import { useState } from 'react';

type Message={role:'user'|'assistant';content:string};
const API=import.meta.env.VITE_AGENT_API_URL||'http://127.0.0.1:8000';
export default function App(){
 const [lang,setLang]=useState<'en'|'ar'>('ar');
 const [token,setToken]=useState('');
 const [draft,setDraft]=useState('');
 const [busy,setBusy]=useState(false);
 const [messages,setMessages]=useState<Message[]>([]);
 const [error,setError]=useState('');
 const rtl=lang==='ar';
 async function send(){
  const text=draft.trim(); if(!text||busy)return;
  setMessages(m=>[...m,{role:'user',content:text}]);setDraft('');setBusy(true);setError('');
  try{
   const response=await fetch(API+'/v1/chat',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({message:text,language:lang})});
   const data=await response.json();if(!response.ok)throw new Error(data.detail||'API request failed');
   setMessages(m=>[...m,{role:'assistant',content:data.answer}]);
  }catch(e){setError(e instanceof Error?e.message:'Connection failed');}
  finally{setBusy(false);}
 }
 return <main dir={rtl?'rtl':'ltr'} className="shell">
  <aside className="sidebar"><div className="brand"><span className="mark">M</span><div><b>MAAROOF</b><small>AGENT OS</small></div></div>
   <div className="side-label">{rtl?'مساحة العمل':'WORKSPACE'}</div><button className="nav active">◈　{rtl?'المحادثة':'Agent Chat'}</button><button className="nav">▦　{rtl?'الذاكرة':'Memory Vault'}</button><button className="nav">⌘　{rtl?'المهارات':'Skills'}</button>
   <div className="side-bottom"><span className="status-dot"/> {rtl?'النظام محلي / API':'Local-first / API-backed'}</div>
  </aside>
  <section className="main"><header><div><div className="eyebrow">PERSONAL INTELLIGENCE WORKSPACE</div><h1>{rtl?'مركز القيادة':'Command Center'}</h1></div><div className="header-actions"><button className="lang" onClick={()=>setLang(rtl?'en':'ar')}>{rtl?'EN':'عربي'}</button><span className="avatar">AM</span></div></header>
   <div className="workspace"><div className="welcome"><div className="orb">✳</div><div className="eyebrow">{rtl?'أحمد معروف • نظام الوكلاء الشخصي':'AHMED MAAROOF • PERSONAL AGENT SYSTEM'}</div><h2>{rtl?'ما الذي نعمل عليه اليوم؟':'What are we working on today?'}</h2><p>{rtl?'اربط المعرفة، حلّل المعلومات، ونفّذ العمل من مساحة واحدة.':'Connect knowledge, analyze information, and move work forward from one workspace.'}</p></div>
    <div className="conversation">{messages.map((m,i)=><article key={i} className={'message '+m.role}><b>{m.role==='user'?(rtl?'أنت':'You'):'MAAROOF'}</b><p>{m.content}</p></article>)}{busy&&<div className="thinking">{rtl?'جاري التفكير...':'Thinking...'}</div>}</div>
    <div className="composer"><textarea value={draft} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send();}}} placeholder={rtl?'اكتب رسالتك أو المهمة التي تريد تنفيذها...':'Ask Maaroof or describe a task...'} />
     <div className="composer-footer"><input aria-label="Backend API token" type="password" value={token} onChange={e=>setToken(e.target.value)} placeholder={rtl?'مفتاح API للخادم':'Backend API token'} /><button disabled={busy||!draft.trim()} onClick={()=>void send()}>{busy?'…':rtl?'إرسال ↑':'Send ↑'}</button></div>
    </div>{error&&<div className="error">{error}</div>}
   </div><footer>MAAROOF AGENT OS <span>FOUNDATION 0.1 • PRIVATE BY DESIGN</span></footer>
  </section>
 </main>
}
