"""Inline chatbot at the bottom of the unified quality dashboard."""
from pathlib import Path
import html
import os

import streamlit as st

from quality_chatbot import (CHAT_VERSION, MAX_QUESTION, fingerprint, generate_answer,
                             load_knowledge, load_encrypted_knowledge, service_error_reason)


@st.cache_resource(show_spinner=False)
def _knowledge(path, modified, key_identity='', _key=''):
    return load_encrypted_knowledge(path, _key) if _key else load_knowledge(path)


def _show_answer(answer, t):
    for paragraph in answer['paragraphs']:
        st.markdown(paragraph['text'])
        citations = []
        for sid in paragraph['sources']:
            label = t('看板', 'Data') if sid.startswith('D') else 'DPCP'
            citations.append(f'<span class="qchat-citation" data-source-id="{html.escape(sid)}">{label} <b>{html.escape(sid)}</b></span>')
        st.markdown('<div class="qchat-citations">' + ''.join(citations) + '</div>', unsafe_allow_html=True)
    if answer.get('follow_up'):
        st.markdown(answer['follow_up'])
    with st.expander(t('查看资料与数据依据', 'View sources and data'), expanded=False):
        for item in answer.get('evidence', []):
            source_kind = t('看板数据', 'Dashboard data') if item['kind'] == 'dashboard' else t('DPCP 资料', 'DPCP document')
            st.markdown(f'<div class="qchat-source-heading"><span>{html.escape(source_kind)} · {html.escape(item["id"])}</span><strong>{html.escape(item["title"])}</strong></div>', unsafe_allow_html=True)
            if item.get('locator'):
                st.caption(item['locator'])
            if item['kind'] == 'dashboard':
                st.code(item['content'], language='json')
            else:
                st.text(item['content'])


@st.fragment
def render_quality_chatbot(root, snapshot, t, get_key, get_setting, post_json):
    stylesheet = Path(root) / 'quality_chatbot.css'
    if stylesheet.is_file():
        st.markdown('<style>' + stylesheet.read_text() + '</style>', unsafe_allow_html=True)
    index = Path(os.environ.get('QUALITY_KNOWLEDGE_INDEX', str(Path(root) / 'quality_knowledge/index.jsonl')))
    encrypted = False
    if not index.is_file():
        bundle = Path(root) / 'assets/quality-knowledge.bin'
        if bundle.is_file():
            index, encrypted = bundle, True
    modified = (index.stat().st_mtime_ns, index.stat().st_size) if index.is_file() else None
    knowledge_key = get_setting(['QUALITY_KNOWLEDGE_KEY'], default='') if encrypted else ''
    try:
        if encrypted and not knowledge_key:
            raise ValueError('knowledge_key_missing')
        knowledge, status = _knowledge(str(index), modified, fingerprint(knowledge_key), knowledge_key)
    except Exception as error:
        print('Quality knowledge unavailable:', 'encrypted=' + str(encrypted),
              'key_present=' + str(bool(knowledge_key)), type(error).__name__, flush=True)
        knowledge, status = [], {'documents': 0, 'available': False}
    if not status['available'] and not modified:
        print('Quality knowledge unavailable: corpus_file_missing', flush=True)
    identity = fingerprint({'data': snapshot, 'knowledge': [modified, fingerprint(knowledge_key), status['available']],
                            'language': st.session_state.lang, 'version': CHAT_VERSION})
    state = st.session_state.setdefault('_quality_chat', {'identity': identity, 'messages': []})
    changed = state['identity'] != identity
    if changed:
        state.update(identity=identity, messages=[])
    with st.container(border=False, key='quality_chatbot'):
        scope = snapshot.get('scope', {})
        communities = ' / '.join(scope.get('communities', []))
        focus = snapshot.get('focused_cc')
        api_key = get_key()
        with st.container(key='quality_chat_header'):
            heading, clear = st.columns([.78, .22], vertical_alignment='center')
            with heading:
                st.markdown('<div class="qchat-heading"><div class="qchat-mark" aria-hidden="true">Q</div><div><p class="qchat-eyebrow">NEA QUALITY</p><h3 class="qchat-title">' + html.escape(t('质量助手', 'Quality Assistant')) + '</h3></div></div>', unsafe_allow_html=True)
            with clear, st.container(key='quality_chat_clear_action'):
                if st.button(t('清空对话', 'Clear chat'), key='quality_chat_clear', icon=':material/delete_sweep:', type='tertiary'):
                    state['messages'] = []
                    st.rerun(scope='fragment')
        scope_text = communities
        if scope.get('suppliers'):
            scope_text += ' · ' + ' / '.join(scope['suppliers'])
        if focus:
            scope_text += f' · {t("质量分析 CC", "Quality analysis CC")} {focus}'
        elif scope.get('ccs'):
            scope_text += ' · CC ' + ', '.join(str(cc) for cc in scope['ccs'][:2])
            if len(scope['ccs']) > 2:
                scope_text += f' +{len(scope["ccs"])-2}'
        dates = f'{scope.get("start", "")} → {scope.get("end", "")}'
        status_text = t(f'DPCP 资料 {status["documents"]} 份', f'{status["documents"]} DPCP documents') if knowledge else t('DPCP 资料待接入', 'DPCP documents unavailable')
        status_class = 'is-ready' if knowledge else 'is-pending'
        st.markdown('<div class="qchat-context"><span class="qchat-scope">' + html.escape(scope_text) + '</span><span class="qchat-dates">' + html.escape(dates) + '</span><span class="qchat-status ' + status_class + '"><i></i>' + html.escape(status_text) + '</span></div>', unsafe_allow_html=True)
        if not knowledge:
            st.info(t('当前筛选数据已接入；DPCP 资料正文尚未加载，暂不能核对资料中的具体要求。',
                      'Current filtered data is connected. DPCP document content is not yet loaded.'))
        if changed:
            st.caption(t('筛选或数据已变化，对话已更新到当前范围。', 'Filters or data changed. Chat now uses the current scope.'))
        if not api_key:
            st.info(t('通义千问尚未配置，聊天暂不可用。', 'Qwen is not configured; chat is currently unavailable.'))
        suggested_question = None
        starters = st.empty()
        if not state['messages']:
            with starters.container(), st.container(key='quality_chat_starters'):
                st.markdown('<div class="qchat-welcome"><h4>' + html.escape(t('从一个具体问题开始', 'Start with a specific question')) + '</h4><p>' + html.escape(t('查 DPCP 资料，解读当前看板。', 'Find DPCP guidance. Understand the current dashboard.')) + '</p></div>', unsafe_allow_html=True)
                selected_product = bool(focus or len(scope.get('ccs', [])) == 1)
                prompts = [
                    ('data', t('**当前质量** 当前最需要关注什么？', '**Current quality** What needs attention?'), ':material/monitoring:', t('当前最需要关注什么？', 'What needs attention in the current dashboard?')),
                    ('product', t('**当前 CC** 这个产品有哪些主要问题？', '**Current CC** What are this product’s main issues?') if selected_product else t('**指标解读** 这些质量指标说明什么？', '**Read the metrics** What do these quality metrics show?'), ':material/center_focus_strong:' if selected_product else ':material/query_stats:', t('这个 CC 的主要问题是什么？', 'What are this CC’s main issues?') if selected_product else t('当前看板的关键质量指标如何解读？', 'How should I read the current dashboard’s key quality metrics?')),
                    ('docs', t('**DPCP 资料** QA 准备有哪些要求？', '**DPCP guidance** What is required for QA preparation?'), ':material/menu_book:', t('资料对 QA 准备有什么要求？', 'What do the documents require for QA preparation?')),
                ]
                for column, (name, label, icon, prompt) in zip(st.columns(3, gap='small'), prompts):
                    with column:
                        if st.button(label, icon=icon, key='quality_chat_quick_' + name, use_container_width=True,
                                     disabled=not bool(api_key) or (name == 'docs' and not knowledge)):
                            suggested_question = prompt
        transcript = st.container(key='quality_chat_transcript')
        for message_index, message in enumerate(state['messages']):
            with transcript, st.container(key=f'quality_chat_{message["role"]}_{message_index}'), st.chat_message(message['role'], avatar=':material/support_agent:' if message['role'] == 'assistant' else ':material/person:'):
                if message['role'] == 'assistant':
                    _show_answer(message['answer'], t)
                else:
                    st.markdown(message['content'])
        typed_question = st.chat_input(t('询问质量资料或当前看板数据…', 'Ask about quality documents or current dashboard data…'),
                                 key='quality_chat_question', max_chars=MAX_QUESTION, disabled=not bool(api_key))
        question = typed_question or suggested_question
        if not question:
            return
        starters.empty()
        history = [{'role': m['role'], 'content': m['content']} for m in state['messages'][-6:]]
        state['messages'].append({'role': 'user', 'content': question})
        with transcript, st.container(key=f'quality_chat_user_{len(state["messages"])-1}'), st.chat_message('user', avatar=':material/person:'):
            st.markdown(question)
        def request(messages):
            response = post_json(get_setting(['DASHSCOPE_BASE_URL', 'QWEN_BASE_URL'],
                default='https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'),
                {'model': get_setting(['QWEN_CHAT_MODEL', 'QWEN_MODEL'], default='qwen-flash'),
                 'messages': messages, 'temperature': .1, 'max_tokens': 2200,
                 'response_format': {'type': 'json_object'}}, {'Authorization': f'Bearer {api_key}'}, timeout=60)
            return response['choices'][0]['message']['content']
        try:
            with transcript, st.spinner(t('正在查资料并核对当前数据…', 'Checking documents and current data…')):
                answer = generate_answer(question, snapshot, knowledge, history, request, st.session_state.lang)
            with transcript, st.container(key=f'quality_chat_assistant_{len(state["messages"])}'), st.chat_message('assistant', avatar=':material/support_agent:'):
                _show_answer(answer, t)
            state['messages'].append({'role': 'assistant', 'answer': answer,
                'content': '\n'.join(p['text'] for p in answer['paragraphs'])})
            state['messages'] = state['messages'][-12:]
        except Exception as error:
            # Provider bodies can contain proprietary text or credentials: never render/log them.
            print('Quality chatbot request rejected:', type(error).__name__, flush=True)
            state['messages'].pop()
            reason = service_error_reason(error)
            if reason == 'quota':
                st.warning(t('聊天服务额度不足，暂时无法回答；请联系看板管理员恢复额度后重试。',
                             'Chat service quota is unavailable. Please contact the dashboard administrator and retry after it is restored.'))
            elif reason == 'configuration':
                st.warning(t('聊天服务配置暂不可用，请联系看板管理员。',
                             'Chat service configuration is unavailable. Please contact the dashboard administrator.'))
            else:
                st.warning(t('本次回答未通过来源核对或服务暂不可用，请重试；未保存未经核对的回答。',
                             'Source verification failed or the service is unavailable. Please retry. No unverified answer was saved.'))
