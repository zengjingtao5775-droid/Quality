import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Streamlit } from 'streamlit-component-lib';
import './style.css';

type Mode = 'label' | 'review';
type Status = 'unreviewed' | 'submitted' | 'returned' | 'approved';
type Outcome = 'labeled' | 'insufficient' | 'out_of_taxonomy' | 'split_needed';
type Gate = { stage: string; total: number; trainable: number } & Record<Status, number>;
type Option = { id: string; name: string; definition: string };
type Sample = {
  id: string; description: string; rawType: string; factory: string; family: string;
  stage: string; process: string; date: string; source: string; record: string;
  status: Status; actor: string; revision: number; labels: string[]; outcome: Outcome;
  reason: string; suggestion: string; suggestionSource: 'dictionary' | 'model'; options: Option[];
};
type View = {
  language: 'zh' | 'en'; gates: Gate[]; mode: Mode; query: string; actor: string; scope: string[];
  queueCount: number; queuePosition: number; sample: Sample | null; message: string; error: string;
};
type Command = { action: 'queue'; mode: Mode; query: string } | {
  action: 'next' | 'submit' | 'approve' | 'return'; id: string; revision: number;
  labels?: string[]; outcome?: Outcome; reason?: string;
};
const statusOrder: Status[] = ['approved', 'submitted', 'returned', 'unreviewed'];
const content = {
  zh: {
    progress: '标注进度', scope: '当前范围', approved: '已复核', submitted: '待复核', returned: '待补充', unreviewed: '未标注',
    trainable: '可训练的单标签', overview: '按检验环节', total: '范围内记录', done: '已复核进度',
    why: '把不同工厂的疵点描述归到同一套标准类型。复核通过后，单标签样本可用于训练。',
    flow: ['确认标准疵点', '第二人复核', '导出训练样本'],
    task: '现在处理这一条', label: '做标注', review: '做复核', actor: '你的标注或复核名称',
    actorHint: '输入名称后可以保存。复核请使用第二个名称。', search: '搜索记录', searchPlaceholder: '原文、工序或记录号', find: '查找', clear: '清空',
    hintLabel: '读原文，确认一个标准疵点。复合描述可多选，信息不足时记录原因。',
    hintReview: '核对原文和已提交的标签。确认后，这条记录计入已复核进度。',
    noLabel: '当前范围没有待标注记录。可以清空搜索或调整上方范围。',
    noReview: '当前名称下没有可复核的记录。检查筛选条件，或换第二位复核人。',
    noRecords: '当前范围没有记录。可以调整范围，或从「数据与评估」导入。',
    candidate: '字典候选', model: '模型候选', standard: '标准疵点', option: '选择标准疵点', detail: '查看原始来源与标注口径',
    next: '下一条', submit: '确认并提交', approve: '通过复核', sendBack: '退回补充', sendBackNow: '确认退回', cancel: '取消退回',
    reason: '说明缺少什么信息或需要核对什么', outcome: '如何处理', process: '工序', type: '原始分类', source: '来源',
    submittedBy: '提交人', reasonRecorded: '原说明', saving: '正在处理…', remove: '移除',
    outcomes: { labeled: '可以标注', insufficient: '信息不足', out_of_taxonomy: '字典缺项', split_needed: '复合描述待拆分' },
  },
  en: {
    progress: 'Labeling progress', scope: 'Current scope', approved: 'Reviewed', submitted: 'Awaiting review', returned: 'Needs clarification', unreviewed: 'Unlabeled',
    trainable: 'Single-label training records', overview: 'By inspection gate', total: 'Records in scope', done: 'Review progress',
    why: 'Normalize defect wording across factories. Reviewed single-label records can be exported for training.',
    flow: ['Choose a canonical defect', 'Get a second review', 'Export training records'],
    task: 'Work on this record', label: 'Label', review: 'Review', actor: 'Annotator or reviewer name',
    actorHint: 'Enter a name to save. Use a second name for review.', search: 'Search records', searchPlaceholder: 'Wording, process or record ID', find: 'Find', clear: 'Clear',
    hintLabel: 'Read the source and choose the defect. Select multiple labels for compound observations or explain missing evidence.',
    hintReview: 'Check the original wording and submitted labels. Approval counts toward reviewed progress.',
    noLabel: 'No records to label here. Clear the search or adjust the scope.',
    noReview: 'No reviews are available for this name. Check the filters or use a second reviewer.',
    noRecords: 'No records in this scope. Adjust the scope or import in Data and evaluation.',
    candidate: 'Dictionary suggestion', model: 'Model suggestion', standard: 'Canonical defect', option: 'Choose a canonical defect', detail: 'View source and definitions',
    next: 'Next record', submit: 'Confirm and submit', approve: 'Approve review', sendBack: 'Return for clarification', sendBackNow: 'Confirm return', cancel: 'Cancel return',
    reason: 'Explain what is missing or what to check', outcome: 'Disposition', process: 'Process', type: 'Original category', source: 'Source',
    submittedBy: 'Submitted by', reasonRecorded: 'Original note', saving: 'Working…', remove: 'Remove',
    outcomes: { labeled: 'Labelable', insufficient: 'Insufficient evidence', out_of_taxonomy: 'Taxonomy gap', split_needed: 'Compound wording to split' },
  },
};
type Copy = typeof content.zh;

function Progress({ gates, copy, scope }: { gates: Gate[]; copy: Copy; scope: string[] }) {
  const sums = Object.fromEntries(['total', 'trainable', ...statusOrder].map(key => [key,
    gates.reduce((count, gate) => count + gate[key as keyof Omit<Gate, 'stage'>], 0),
  ])) as Omit<Gate, 'stage'>;
  const percentage = sums.total ? sums.approved / sums.total * 100 : 0;
  const number = (value: number) => value.toLocaleString();
  return <section className="overview" aria-labelledby="progress-title">
    <div className="overview-intro">
      <div className="eyebrow">{copy.scope} <span>{scope.join(' / ')}</span></div>
      <h1 id="progress-title">{copy.progress}</h1>
      <p>{copy.why}</p>
    </div>
    <ol className="flow">{copy.flow.map((step, i) => <li key={step}><b>{i + 1}</b>{step}</li>)}</ol>
    <div className="score">
      <div className="score-heading"><span>{copy.done}</span><strong>{number(sums.approved)} <small>/ {number(sums.total)}</small></strong><b>{percentage > 0 && percentage < 0.01 ? '<0.01' : percentage.toFixed(2)}%</b></div>
      <div className="meter" role="progressbar" aria-label={copy.done} aria-valuenow={sums.approved} aria-valuemin={0} aria-valuemax={sums.total || 1}>
        {statusOrder.map(status => <span key={status} className={status} style={{ width: `${sums.total ? sums[status] / sums.total * 100 : 0}%` }} />)}
      </div>
      <div className="totals">
        {statusOrder.map(status => <div key={status}><i className={status} /><span>{copy[status]}</span><b>{number(sums[status])}</b></div>)}
        <div className="trainable"><span>{copy.trainable}</span><b>{number(sums.trainable)}</b></div>
      </div>
    </div>
    <div className="gate-list" aria-label={copy.overview}>
      {gates.map(gate => <div className="gate" key={gate.stage}>
        <b>{gate.stage}</b><span aria-label={`${copy.approved} ${number(gate.approved)} · ${copy.total} ${number(gate.total)}`}>{number(gate.approved)} / {number(gate.total)}</span>
      </div>)}
    </div>
  </section>;
}

function RecordCard({ sample, mode, actor, copy, disabled, send }: {
  sample: Sample; mode: Mode; actor: string; copy: Copy; disabled: boolean; send: (event: Command) => void;
}) {
  const [labels, setLabels] = useState(sample.labels.length ? sample.labels : sample.suggestion && sample.status === 'unreviewed' ? [sample.suggestion] : []);
  const [outcome, setOutcome] = useState(sample.outcome);
  const [reason, setReason] = useState(sample.reason);
  const [returning, setReturning] = useState(false);
  const isReview = mode === 'review';
  const labelRequired = outcome === 'labeled' && !labels.length;
  const invalid = disabled || !actor.trim() || labelRequired || ((outcome !== 'labeled' || returning) && !reason.trim());
  const submit = (action: 'submit' | 'approve' | 'return') => send({ action, id: sample.id, revision: sample.revision, labels, outcome, reason });
  const suggestion = sample.options.find(option => option.id === sample.suggestion);

  return <div className="record">
    <div className="record-context"><span>{sample.stage}</span><b>{sample.factory}</b><span>{sample.family}</span>{sample.date && <time>{sample.date}</time>}</div>
    <p className="description">{sample.description}</p>
    {sample.process && <p className="small-text">{copy.process} · {sample.process}</p>}
    {isReview && <p className="small-text">{copy.submittedBy} · {sample.actor}</p>}
    {sample.status === 'returned' && sample.reason && <p className="small-text">{copy.reasonRecorded} · {sample.reason}</p>}
    <details><summary>{copy.detail}</summary>
      <div className="details">{copy.source} · {sample.source} · {sample.record}{sample.rawType && <p>{copy.type} · {sample.rawType}</p>}
        {sample.options.filter(option => labels.includes(option.id) && option.definition).map(option => <p key={option.id}>{option.name} · {option.definition}</p>)}</div>
    </details>
    <form onSubmit={event => { event.preventDefault(); if (!invalid) submit(returning ? 'return' : isReview ? 'approve' : 'submit'); }}>
      <div className="field-row">
        <label>{copy.outcome}<select value={outcome} onChange={event => setOutcome(event.currentTarget.value as Outcome)}>
          {Object.entries(copy.outcomes).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
        {outcome === 'labeled' && <label>{copy.standard}<select value="" onChange={event => setLabels([...labels, event.currentTarget.value])}>
          <option value="" disabled>{copy.option}</option>
          {sample.options.filter(option => !labels.includes(option.id)).map(option => <option value={option.id} key={option.id}>{option.name} · {option.id}</option>)}
        </select></label>}
      </div>
      {outcome === 'labeled' && <div className="chips">
        {sample.options.filter(option => labels.includes(option.id)).map(option => <button type="button" className="chip" key={option.id} aria-label={`${copy.remove} ${option.name}`} onClick={() => setLabels(labels.filter(label => label !== option.id))}>{option.name} <span>×</span></button>)}
        {suggestion && !isReview && <span className="suggestion">{sample.suggestionSource === 'model' ? copy.model : copy.candidate} · {suggestion.name}</span>}
      </div>}
      {(returning || outcome !== 'labeled') && <label className="note">{copy.reason}<textarea value={reason} maxLength={1000} onChange={event => setReason(event.currentTarget.value)} /></label>}
      <div className="actions">
        <button className="primary" type="submit" disabled={invalid}>{returning ? copy.sendBackNow : isReview ? copy.approve : copy.submit}</button>
        {isReview && <button type="button" disabled={disabled} onClick={() => setReturning(!returning)}>{returning ? copy.cancel : copy.sendBack}</button>}
        <button className="next" type="button" disabled={disabled} onClick={() => send({ action: 'next', id: sample.id, revision: sample.revision })}>{copy.next} <span aria-hidden="true">→</span></button>
      </div>
    </form>
  </div>;
}

function Workbench({ view, busy, send }: { view: View; busy: boolean; send: (event: Command, actor: string) => void }) {
  const copy = content[view.language];
  const [actor, setActor] = useState(view.actor);
  const [query, setQuery] = useState(view.query);
  const reviewer = view.mode === 'review';
  const search = (mode: Mode, value = query) => send({ action: 'queue', mode, query: value }, actor);
  return <main>
    <Progress gates={view.gates} copy={copy} scope={view.scope} />
    <section className="work" aria-labelledby="task-title">
      <div className="work-heading"><h2 id="task-title">{copy.task}</h2>
        <span className="queue-count">{view.queuePosition.toLocaleString()} / {view.queueCount.toLocaleString()}</span>
      </div>
      <div className="tools">
        <div className="switch" aria-label={copy.task}>
          <button type="button" aria-pressed={!reviewer} disabled={busy} onClick={() => search('label')}>{copy.label}</button>
          <button type="button" aria-pressed={reviewer} disabled={busy} onClick={() => search('review')}>{copy.review}</button>
        </div>
        <label className="identity">{copy.actor}<input value={actor} maxLength={80} autoComplete="off" onChange={event => setActor(event.currentTarget.value)} /></label>
        <form className="search" onSubmit={event => { event.preventDefault(); search(view.mode); }}>
          <label>{copy.search}<input placeholder={copy.searchPlaceholder} value={query} maxLength={150} onChange={event => setQuery(event.currentTarget.value)} /></label>
          <button type="submit" disabled={busy}>{copy.find}</button>
          {query && <button type="button" disabled={busy} onClick={() => { setQuery(''); search(view.mode, ''); }}>{copy.clear}</button>}
        </form>
      </div>
      <p className="work-hint">{reviewer ? copy.hintReview : copy.hintLabel} {!actor.trim() && copy.actorHint}</p>
      {view.message && <p className="feedback" role="status">{view.message}</p>}
      {view.error && <p className="feedback error" role="alert">{view.error}</p>}
      {busy && <p className="small-text" role="status">{copy.saving}</p>}
      {view.sample ? <RecordCard key={`${view.mode}/${view.sample.id}/${view.sample.revision}`} sample={view.sample} copy={copy} mode={view.mode} actor={actor} disabled={busy} send={event => send(event, actor)} />
        : <p className="empty">{view.gates.every(gate => gate.total === 0) ? copy.noRecords : reviewer ? copy.noReview : copy.noLabel}</p>}
    </section>
  </main>;
}

function Frame() {
  const [view, setView] = useState<View | null>(null);
  const [busy, setBusy] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const receive = (event: Event) => {
      const next = (event as CustomEvent<{ args: View }>).detail.args;
      document.documentElement.lang = next.language === 'zh' ? 'zh-CN' : 'en';
      setView(next);
      setBusy(false);
    };
    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, receive);
    Streamlit.setComponentReady();
    const resize = new ResizeObserver(entries => Streamlit.setFrameHeight(Math.ceil(entries[0].target.getBoundingClientRect().height) + 2));
    if (root.current) resize.observe(root.current);
    return () => { Streamlit.events.removeEventListener(Streamlit.RENDER_EVENT, receive); resize.disconnect(); };
  }, []);
  return <div ref={root}>{view && <Workbench key={view.scope.join('/')} view={view} busy={busy} send={(event, actor) => {
    setBusy(true);
    Streamlit.setComponentValue({ ...event, actor, nonce: crypto.randomUUID() });
  }} />}</div>;
}

createRoot(document.getElementById('root')!).render(<Frame />);
