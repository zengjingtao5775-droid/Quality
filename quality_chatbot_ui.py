"""Inline chatbot at the bottom of the unified quality dashboard."""
from pathlib import Path
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
        st.caption(' '.join('[' + item + ']' for item in paragraph['sources']))
    if answer.get('follow_up'):
        st.markdown(answer['follow_up'])
    with st.expander(t('查看资料与数据依据', 'View sources and data'), expanded=False):
        for item in answer.get('evidence', []):
            st.markdown(f'**[{item["id"]}] {item["title"]}**')
            if item.get('locator'):
                st.caption(item['locator'])
            if item['kind'] == 'dashboard':
                st.code(item['content'], language='json')
            else:
                st.text(item['content'])


@st.fragment
def render_quality_chatbot(root, snapshot, t, get_key, get_setting, post_json):
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
    with st.container(border=True, key='quality_chatbot'):
        heading, clear = st.columns([.8, .2], vertical_alignment='center')
        with heading:
            st.subheader(t('质量助手', 'Quality Assistant'))
        with clear:
            if st.button(t('清空对话', 'Clear chat'), key='quality_chat_clear', use_container_width=True):
                state['messages'] = []
                st.rerun(scope='fragment')
        scope = snapshot.get('scope', {})
        communities = ' / '.join(scope.get('communities', []))
        focus = snapshot.get('focused_cc')
        scope_label = f'{communities} · {scope.get("start", "")} → {scope.get("end", "")}'
        if focus:
            scope_label += f' · {t("质量分析 CC", "Quality analysis CC")} {focus}'
        st.caption(scope_label)
        if knowledge:
            st.caption(t(f'DPCP 资料 {status["documents"]} 份 · 已接入当前筛选数据',
                         f'{status["documents"]} DPCP documents · Current filtered data connected'))
        else:
            st.info(t('当前筛选数据已接入；DPCP 资料正文尚未加载，暂不能核对资料中的具体要求。',
                      'Current filtered data is connected. DPCP document content is not yet loaded.'))
        if changed:
            st.caption(t('筛选或数据已变化，对话已更新到当前范围。', 'Filters or data changed. Chat now uses the current scope.'))
        api_key = get_key()
        if not api_key:
            st.info(t('通义千问尚未配置，聊天暂不可用。', 'Qwen is not configured; chat is currently unavailable.'))
        if not state['messages']:
            st.markdown(t('可以问：当前最需要关注什么？这个 CC 的主要问题是什么？资料对 QA 准备有什么要求？',
                          'Ask: What needs attention? What are this CC’s main issues? What do the documents require for QA preparation?'))
        transcript = st.container()
        for message in state['messages']:
            with transcript, st.chat_message(message['role']):
                if message['role'] == 'assistant':
                    _show_answer(message['answer'], t)
                else:
                    st.markdown(message['content'])
        question = st.chat_input(t('询问质量资料或当前看板数据…', 'Ask about quality documents or current dashboard data…'),
                                 key='quality_chat_question', max_chars=MAX_QUESTION, disabled=not bool(api_key))
        if not question:
            return
        history = [{'role': m['role'], 'content': m['content']} for m in state['messages'][-6:]]
        state['messages'].append({'role': 'user', 'content': question})
        with transcript, st.chat_message('user'):
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
            with transcript, st.chat_message('assistant'):
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
