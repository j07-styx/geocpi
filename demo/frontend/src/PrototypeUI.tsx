import type { ReactNode } from "react";

export type Screen = "predict" | "explore" | "glossary" | "compare" | "notebook";

const PATHS: Record<string, ReactNode> = {
  predict: <><path d="M12 5v14M5 12h14"/></>,
  explore: <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>,
  glossary: <><path d="M7 4h13M7 10h13M7 16h13M3 4h.01M3 10h.01M3 16h.01"/></>,
  compare: <><path d="M4 5h7m-3-3v6M13 19h7m-3-3v6M9 17l6-10"/></>,
  notebook: <><rect x="5" y="3" width="15" height="18" rx="2"/><path d="M9 7h7M9 11h7M9 15h5M3 6h3M3 12h3M3 18h3"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  info: <><circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/></>,
  arrow: <path d="M5 12h14m-6-6 6 6-6 6"/>,
  reload: <><path d="M20 11a8 8 0 1 0-2.4 6M20 4v7h-7"/></>,
  book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5V5.5"/></>,
  external: <><path d="M14 3h7v7M21 3l-9 9"/><path d="M21 13v7H4V3h7"/></>,
  download: <><path d="M12 3v13m-5-5 5 5 5-5M4 20h16"/></>,
  star: <path d="m12 2 3 6.2 6.8 1-4.9 4.8 1.2 6.8L12 17.6l-6.1 3.2 1.2-6.8-4.9-4.8 6.8-1z"/>,
  trash: <><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/></>,
  save: <><path d="M4 4h14l2 3v13H4zM7 4v7h9V4M8 20v-6h8v6"/></>,
};
export function Symbol({ name, size=18, className="" }: {name:string;size?:number;className?:string}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    {PATHS[name] || PATHS.info}
  </svg>;
}
export function BrandMark() {
  return <svg viewBox="0 0 36 36" width="30" height="30" aria-hidden="true" className="brand-geometry">
    <path d="M18 2.6 31.2 10.1V25.5L18 33.3 4.8 25.5V10.1z" fill="none" stroke="currentColor" strokeWidth="2.15"/>
    <path d="m18 2.6.1 15.1 13.1 7.8M4.8 10.1l13.3 7.6 13.1-7.6M4.8 25.5l13.3-7.8-.1 15.6" fill="none" stroke="currentColor" strokeWidth="1.5" opacity=".75"/>
    <circle cx="18.1" cy="17.7" r="2.25" fill="currentColor"/>
  </svg>;
}
export function InfoTip({ label, children }: {label:string;children:ReactNode}) {
  return <details className="proto-tip">
    <summary aria-label={`Information about ${label}`} title={label}><Symbol name="info" size={15}/></summary>
    <div className="proto-tip-content"><strong>{label}</strong><p>{children}</p></div>
  </details>;
}
export function PageTitle({ eyebrow, title, description, actions }: {eyebrow:string;title:string;description:string;actions?:ReactNode}) {
  return <div className="proto-page-heading"><div><span className="proto-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{actions && <div className="proto-heading-actions">{actions}</div>}</div>;
}
export function EmptyMessage({ title, description }: {title:string;description:string}) {
  return <div className="proto-empty"><div className="proto-empty-icon">⌁</div><strong>{title}</strong><p>{description}</p></div>;
}
