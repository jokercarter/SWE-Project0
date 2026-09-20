import Markdown from 'react-markdown';
/** Private Markdown never auto-fetches remote images from documents/model output. */
export default function SafeMarkdown({children}:{children:string}){return <Markdown components={{img:({alt})=><span className="muted">[Image: {alt||'attachment'}]</span>,a:({href,children})=><a href={href} rel="noopener noreferrer">{children}</a>}}>{children}</Markdown>;}
