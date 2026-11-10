import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Streamlit } from 'streamlit-component-lib';
import './style.css';

type Status = 'labeled' | 'uncertain' | 'remaining';
type Gate = { stage: string; total: number; trainable: number } & Record<Status, number>;
type Sample = {
  id: string; description: string; rawType: string; factory: string; family: string;
  stage: string; process: string; date: string; source: string; record: string; revision: number;
  suggestion: string; options: { id: string; name: string }[];
};
type View = {
  language: 'zh' | 'en'; gates: Gate[]; query: string; scope: string[]; scopeKey: string;
  queueCount: number; queuePosition: number; sample: Sample | null; canUndo: boolean; message: string; error: string;
  acknowledgedEvent: string | null;
};
type Command = { action: 'search'; query: string } | { action: 'undo' } | {
  action: 'next' | 'answer'; id: string; revision: number; choice?: string;
};
const statusOrder: Status[] = ['labeled', 'uncertain', 'remaining'];
const content = {
  zh: {
    progress: '标注进度', scope: '当前范围', labeled: '已标注', uncertain: '待判断', remaining: '待作答',
    trainable: '可训练单标签', overview: '按检验环节', total: '范围内记录', done: '已处理',
    task: '这条记录属于哪类疵点？',
    search: '搜索记录', placeholder: '疵点、工序或记录号', find: '查找', clear: '清空',
    empty: '当前范围没有待作答记录。可以清空搜索或调整上方范围。',
    noRecords: '当前范围没有记录。可以调整范围，或从「数据与评估」导入。',
    other: '选其他类型', unsure: '暂无法判断', options: '选择一个标准类型',
    detail: '查看原始来源', process: '工序', type: '原始分类', next: '跳过', undo: '撤销上一条', saving: '保存中…',
  },
  en: {
    progress: 'Labeling progress', scope: 'Current scope', labeled: 'Labeled', uncertain: 'Undetermined', remaining: 'Unanswered',
    trainable: 'Single-label training records', overview: 'By inspection gate', total: 'Records in scope', done: 'Answered',
    task: 'Which defect does this record describe?',
    search: 'Find a record', placeholder: 'Defect, process or record ID', find: 'Find', clear: 'Clear',
    empty: 'No unanswered records in this selection. Clear the search or adjust the filters.',
    noRecords: 'No records in this scope. Adjust the filters or import in Data and evaluation.',
    other: 'Choose another type', unsure: 'Unable to determine', options: 'Choose one canonical type',
    detail: 'View source record', process: 'Process', type: 'Original category', next: 'Skip', undo: 'Undo last answer', saving: 'Saving…',
  },
};
type Copy = typeof content.zh;

function Progress({ gates, copy, scope }: { gates: Gate[]; copy: Copy; scope: string[] }) {
  const sums = Object.fromEntries(['total', 'trainable', ...statusOrder].map(key => [key,
    gates.reduce((count, gate) => count + gate[key as keyof Omit<Gate, 'stage'>], 0),
  ])) as Omit<Gate, 'stage'>;
  const processed = sums.labeled + sums.uncertain;
  const percentage = sums.total ? processed / sums.total * 100 : 0;
  const number = (value: number) => value.toLocaleString();
  return <section className="overview" aria-labelledby="progress-title">
    <div className="overview-intro">
      <div className="eyebrow">{copy.scope} <span>{scope.join(' / ')}</span></div>
      <h1 id="progress-title">{copy.progress}</h1>
    </div>
    <div className="score">
      <div className="score-heading"><span>{copy.done}</span><strong>{number(processed)} <small>/ {number(sums.total)}</small></strong><b>{percentage > 0 && percentage < 0.01 ? '<0.01' : percentage.toFixed(2)}%</b></div>
      <div className="meter" role="progressbar" aria-label={copy.done} aria-valuenow={processed} aria-valuemin={0} aria-valuemax={sums.total || 1}>
        {statusOrder.map(status => <span key={status} className={status} style={{ width: `${sums.total ? sums[status] / sums.total * 100 : 0}%` }} />)}
      </div>
      <div className="totals">
        {statusOrder.map(status => <div key={status}><i className={status} /><span>{copy[status]}</span><b>{number(sums[status])}</b></div>)}
        <div className="trainable"><span>{copy.trainable}</span><b>{number(sums.trainable)}</b></div>
      </div>
    </div>
    <div className="gate-list" aria-label={copy.overview}>
      {gates.map(gate => <div className="gate" key={gate.stage}>
        <b>{gate.stage}</b><span aria-label={`${copy.done} ${number(gate.labeled + gate.uncertain)} · ${copy.total} ${number(gate.total)}`}>{number(gate.labeled + gate.uncertain)} / {number(gate.total)}</span>
      </div>)}
    </div>
  </section>;
}

function RecordCard({ sample, copy, busy, send }: {
  sample: Sample; copy: Copy; busy: boolean; send: (event: Command) => void;
}) {
  const suggestion = sample.options.find(option => option.id === sample.suggestion);
  const answer = (choice: string) => send({ action: 'answer', id: sample.id, revision: sample.revision, choice });
  return <div className="record">
    <div className="record-context"><span>{sample.stage}</span><b>{sample.factory}</b><span>{sample.family}</span>{sample.date && <time>{sample.date}</time>}</div>
    <p className="description">{sample.description}</p>
    <div className="choices">
      {suggestion && <button className="choice suggested" type="button" disabled={busy} onClick={() => answer(suggestion.id)}>
        <span className="letter">A</span>{suggestion.name}
      </button>}
      <label className="choice alternative">
        <span className="letter" aria-hidden="true">B</span>
        <select aria-label={copy.options} value="" disabled={busy} onChange={event => {
          if (event.currentTarget.value) answer(event.currentTarget.value);
        }}>
          <option value="">{copy.other}</option>
          {sample.options.filter(option => option.id !== suggestion?.id).map(option => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>
      </label>
    </div>
    <div className="actions">
      <button type="button" disabled={busy} onClick={() => answer('unsure')}>{copy.unsure}</button>
      <button className="next" type="button" disabled={busy} onClick={() => send({ action: 'next', id: sample.id, revision: sample.revision })}>{copy.next} <span aria-hidden="true">→</span></button>
    </div>
    <details><summary>{copy.detail}</summary><div className="details">{sample.source} · {sample.record}{sample.process && <p>{copy.process} · {sample.process}</p>}{sample.rawType && <p>{copy.type} · {sample.rawType}</p>}</div></details>
  </div>;
}

function Workbench({ view, action, send }: { view: View; action: Command['action'] | null; send: (event: Command) => void }) {
  const copy = content[view.language];
  const busy = action !== null;
  const [query, setQuery] = useState(view.query);
  return <main>
    <section className="work" aria-labelledby="task-title">
      <div className="work-heading"><h2 id="task-title">{copy.task}</h2>
        <span className="queue-count">{view.queuePosition.toLocaleString()} / {view.queueCount.toLocaleString()}</span>
      </div>
      {view.sample ? <RecordCard key={`${view.sample.id}/${view.sample.revision}`} sample={view.sample} copy={copy} busy={busy} send={send} />
        : <p className="empty">{view.gates.every(gate => gate.total === 0) ? copy.noRecords : copy.empty}</p>}
      <div className="feedback" aria-live="polite">
        {action === 'answer' ? <span>{copy.saving}</span>
          : view.error ? <span className="error" role="alert">{view.error}</span> : <span>{view.message}</span>}
        {view.canUndo && <button type="button" disabled={busy} onClick={() => send({ action: 'undo' })}>{copy.undo}</button>}
      </div>
      <details className="lookup">
        <summary>{copy.search}</summary>
        <form className="search" onSubmit={event => { event.preventDefault(); send({ action: 'search', query }); }}>
          <input aria-label={copy.search} placeholder={copy.placeholder} value={query} maxLength={150} onChange={event => setQuery(event.currentTarget.value)} />
          <button type="submit" disabled={busy}>{copy.find}</button>
          {query && <button type="button" disabled={busy} onClick={() => { setQuery(''); send({ action: 'search', query: '' }); }}>{copy.clear}</button>}
        </form>
      </details>
    </section>
    <Progress gates={view.gates} copy={copy} scope={view.scope} />
  </main>;
}

function Frame() {
  const [view, setView] = useState<View | null>(null);
  const [action, setAction] = useState<Command['action'] | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const pending = useRef<string | null>(null);
  useEffect(() => {
    const receive = (event: Event) => {
      const next = (event as CustomEvent<{ args: View }>).detail.args;
      document.documentElement.lang = next.language === 'zh' ? 'zh-CN' : 'en';
      setView(next);
      if (pending.current && pending.current === next.acknowledgedEvent) {
        pending.current = null;
        setAction(null);
      }
    };
    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, receive);
    Streamlit.setComponentReady();
    const resize = new ResizeObserver(entries => Streamlit.setFrameHeight(Math.ceil(entries[0].target.getBoundingClientRect().height) + 2));
    if (root.current) resize.observe(root.current);
    return () => { Streamlit.events.removeEventListener(Streamlit.RENDER_EVENT, receive); resize.disconnect(); };
  }, []);
  return <div ref={root}>{view && <Workbench key={view.scopeKey} view={view} action={action} send={event => {
    if (pending.current) return;
    const nonce = crypto.randomUUID();
    pending.current = nonce;
    setAction(event.action);
    Streamlit.setComponentValue({ ...event, nonce });
  }} />}</div>;
}

createRoot(document.getElementById('root')!).render(<Frame />);
