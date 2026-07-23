const tokenFromHash = new URLSearchParams(location.hash.slice(1)).get('token');
if (tokenFromHash) { sessionStorage.setItem('atr-control-token', tokenFromHash); history.replaceState(null, '', location.pathname); }
const token = sessionStorage.getItem('atr-control-token') || '';
const translations = {
  en: {
    pause:'Pause', resume:'Resume', endMeeting:'End meeting', newMeeting:'New meeting', topicLabel:'Topic',
    topicPlaceholder:'What should the team decide or verify?', participantsLabel:'Participants (comma separated)',
    firstSpeaker:'First speaker', startMeeting:'Start meeting', participantsHeading:'Participants',
    joinInstructions:'Join instructions',
    inviteHelp:'Paste one instruction into each already-open AI session. Tokens grant access only to that participant in this meeting.',
    noMeeting:'No meeting yet', createHint:'Create a meeting to begin.', everyone:'Everyone', messagePlaceholder:'Human message or decision',
    send:'Send', active:'active', paused:'paused', ended:'ended', opening:'opening speaker', openFloor:'open floor', messages:'AI messages', activeNow:'active now', notJoined:'not joined yet',
    lastSeen:ago=>`last contact ${ago} ago`, secondsAgo:value=>`${value}s`, minutesAgo:value=>`${value}m`, hoursAgo:value=>`${value}h`,
    copyJoin:'Copy join instruction', copied:'Copied', endConfirm:'End this meeting?', missingToken:'Missing control token. Start the server and open the URL it prints.',
    helpTitle:'How to use AI Team Room',
    helpHtml:`<p>Bring the AI coding sessions you already have open into one local meeting.</p><ol><li>Create a topic, participant list, and first speaker.</li><li>Copy each join instruction into that participant's existing AI session.</li><li>The first speaker opens the AI discussion. The floor is then open: participants repeat <b>wait → investigate/work → send → wait</b> without forced rotation.</li><li>Select a recipient to address one AI or everyone. The human can pause, resume, or end the meeting; there is no automatic turn-limit ending.</li></ol><h3>Keyboard</h3><p><b>Enter</b>: send · <b>Shift+Enter</b>: new line</p><h3>Permission boundary</h3><p>Joining never authorizes file changes, paid compute, destructive actions, commits, pushes, or broader permissions.</p><div class="about">2026-07-23 · Madoro Studio · AI Team Room 0.2.0</div>`,
    command:(name,command)=>`You are invited as ${name} to an AI Team Room from this already-open work session. Keep this session's existing context, tools, workspace, and permission boundaries. Run this exact command: ${command}. Read the returned protocol and continue wait -> investigate/work -> send -> wait until the meeting ends.`
  },
  ko: {
    pause:'일시정지', resume:'재개', endMeeting:'회의 종료', newMeeting:'새 회의', topicLabel:'회의 주제',
    topicPlaceholder:'팀이 결정하거나 검증할 내용을 입력하세요', participantsLabel:'참가자 (쉼표로 구분)',
    firstSpeaker:'첫 발언자', startMeeting:'회의 시작', participantsHeading:'참가자',
    joinInstructions:'참가 안내',
    inviteHelp:'각 안내문을 현재 작업 중인 해당 AI 세션에 한 번 붙여 넣으세요. 초대 토큰은 이 회의의 해당 참가자에게만 유효합니다.',
    noMeeting:'진행 중인 회의가 없습니다', createHint:'새 회의를 만들어 시작하세요.', everyone:'모두', messagePlaceholder:'사람의 발언 또는 결정',
    send:'보내기', active:'진행 중', paused:'일시정지', ended:'종료', opening:'첫 발언자', openFloor:'자유발언', messages:'AI 발언', activeNow:'현재 접속 중', notJoined:'아직 참가하지 않음',
    lastSeen:ago=>`마지막 접속 ${ago} 전`, secondsAgo:value=>`${value}초`, minutesAgo:value=>`${value}분`, hoursAgo:value=>`${value}시간`,
    copyJoin:'참가 안내문 복사', copied:'복사됨', endConfirm:'이 회의를 종료할까요?', missingToken:'제어 토큰이 없습니다. 서버를 실행한 뒤 출력된 주소를 여세요.',
    helpTitle:'AI Team Room 사용법',
    helpHtml:`<p>현재 작업 중인 AI 코딩 세션들을 하나의 로컬 회의에 참여시킵니다.</p><ol><li>회의 주제, 참가자, 첫 발언자를 정해 회의를 만듭니다.</li><li>참가자별 안내문을 복사해 해당 AI의 현재 작업 세션에 붙여 넣습니다.</li><li>첫 발언자가 AI 토론을 시작한 뒤 자유발언으로 전환됩니다. AI는 강제 교대 없이 <b>대기 → 조사/작업 → 발언 → 대기</b>를 반복합니다.</li><li>수신자를 골라 한 AI 또는 모두에게 말할 수 있습니다. 사용자가 직접 일시정지, 재개 또는 종료하며 발언 수에 따른 자동 종료는 없습니다.</li></ol><h3>키보드</h3><p><b>Enter</b>: 전송 · <b>Shift+Enter</b>: 줄바꿈</p><h3>권한 경계</h3><p>회의 참가는 파일 수정, 유료 연산, 파괴적 작업, 커밋, 푸시 또는 권한 확대를 자동 승인하지 않습니다.</p><div class="about">2026-07-23 · Madoro Studio · AI Team Room 0.2.0</div>`,
    command:(name,command)=>`현재 실제 작업 세션에서 ${name} 참가자로 AI Team Room 회의에 참가하라. 이 세션의 기존 대화 맥락, 도구, 작업공간, 권한 경계를 그대로 유지하라. 다음 명령을 그대로 실행하라: ${command}. 반환된 참가 규약을 읽고 회의가 끝날 때까지 대기 → 조사/작업 → 발언 → 대기를 반복하라.`
  }
};
let language = localStorage.getItem('atr-language') || 'en';
let current = null, invitations = {}, joinCommands = {}, lastCursor = 0;
const $ = id => document.getElementById(id);
const t = key => translations[language][key] ?? key;
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function applyLanguage() {
  document.documentElement.lang=language; $('language').value=language;
  document.querySelectorAll('[data-i18n]').forEach(node=>node.textContent=t(node.dataset.i18n));
  $('new-topic').placeholder=t('topicPlaceholder'); $('text').placeholder=t('messagePlaceholder');
  $('help-title').textContent=t('helpTitle'); $('help-body').innerHTML=t('helpHtml');
  if(current) render(lastResult); else {$('topic').textContent=t('noMeeting'); if(!token) $('state').textContent=t('missingToken');}
}
async function api(path, options={}) {
  const headers = {'Authorization':`Bearer ${token}`,'Content-Type':'application/json',...(options.headers||{})};
  const response = await fetch(path,{...options,headers}); const result = await response.json();
  if(!response.ok) throw new Error(result.error || response.statusText); return result;
}
async function copy(text, button) { await navigator.clipboard.writeText(text); const old=button.textContent; button.textContent=t('copied'); setTimeout(()=>button.textContent=old,900); }
let lastResult={meeting:null,messages:[],presence:[],cursor:0};
const AUTO_SCROLL_THRESHOLD=80;
const ACTIVE_PRESENCE_MS=45_000;
function isNearMessageBottom(container){
  return container.scrollHeight-container.scrollTop-container.clientHeight<=AUTO_SCROLL_THRESHOLD;
}
function presenceText(lastSeenAt){
  if(!lastSeenAt) return t('notJoined');
  const elapsed=Math.max(0,Date.now()-Date.parse(lastSeenAt));
  if(elapsed<=ACTIVE_PRESENCE_MS) return t('activeNow');
  const seconds=Math.floor(elapsed/1000);
  const ago=seconds<60?t('secondsAgo')(seconds):seconds<3600?t('minutesAgo')(Math.floor(seconds/60)):t('hoursAgo')(Math.floor(seconds/3600));
  return t('lastSeen')(ago);
}
function render(result) {
  lastResult=result; if(result.invitations) invitations=result.invitations; if(result.join_commands) joinCommands=result.join_commands; current=result.meeting;
  const open=current && current.status!=='ended';
  $('create').hidden=open; $('controls').hidden=!open; $('composer').hidden=!open; $('pause').disabled=!open; $('end').disabled=!open;
  if(!current){$('topic').textContent=t('noMeeting');return;}
  $('topic').textContent=current.topic;
  const floor=current.next_speaker==='all'?t('openFloor'):`${t('opening')}: ${current.next_speaker}`;
  $('state').innerHTML=`<span class="status">${esc(t(current.status))}</span> · <b>${esc(floor)}</b> · ${t('messages')} ${current.turn_count}`;
  $('pause').textContent=current.status==='paused'?t('resume'):t('pause');
  const presence=new Map((result.presence||[]).map(p=>[p.participant,p.last_seen_at]));
  $('presence').innerHTML=current.participants.map(p=>`<div class="presence"><b>${esc(p)}</b> · ${esc(presenceText(presence.get(p)))}</div>`).join('');
  const selectedRecipient=$('recipient').value;
  $('recipient').innerHTML=`<option value="all">${t('everyone')}</option>`+current.participants.map(p=>`<option value="${esc(p)}">${esc(p)}</option>`).join('');
  if(selectedRecipient==='all'||current.participants.includes(selectedRecipient)) $('recipient').value=selectedRecipient;
  $('invites').innerHTML=current.participants.map(p=>`<div class="card"><b>${esc(p)}</b><br><button data-copy="${esc(p)}">${t('copyJoin')}</button></div>`).join('');
  document.querySelectorAll('[data-copy]').forEach(button=>button.onclick=()=>copy(t('command')(button.dataset.copy,joinCommands[button.dataset.copy]),button));
  const messages=result.messages||[];
  if(messages.length || lastCursor===0){
    const container=$('messages');
    const initialLoad=lastCursor===0;
    const followNewest=initialLoad||isNearMessageBottom(container);
    if(initialLoad) container.innerHTML='';
    for(const m of messages){
      if(container.querySelector(`[data-message="${m.id}"]`)) continue;
      const node=document.createElement('article'); node.className=`message ${m.sender}`; node.dataset.message=m.id;
      node.innerHTML=`<div class="meta">${esc(m.sender)} → ${esc(m.recipient==='all'?t('everyone'):m.recipient)} · ${esc(m.kind)} · ${new Date(m.created_at).toLocaleTimeString(language)}</div><div class="bubble">${esc(m.text)}</div>`;
      container.appendChild(node);
    }
    lastCursor=Math.max(lastCursor,result.cursor||0);
    if(followNewest) container.scrollTop=container.scrollHeight;
  }
}
async function refresh(){try{render(await api('/api/state'));}catch(e){$('state').textContent=e.message;}}
$('language').onchange=()=>{language=$('language').value;localStorage.setItem('atr-language',language);applyLanguage();};
$('help').onclick=()=>{$('help-dialog').showModal();}; $('help-close').onclick=()=>{$('help-dialog').close();};
$('start').onclick=async()=>{try{const result=await api('/api/meetings',{method:'POST',body:JSON.stringify({topic:$('new-topic').value,participants:$('new-participants').value.split(',').map(x=>x.trim()).filter(Boolean),first_speaker:$('new-first').value.trim()})});invitations=result.invitations;joinCommands=result.join_commands;lastCursor=0;await refresh();}catch(e){$('create-error').textContent=e.message;}};
$('send').onclick=async()=>{const recipient=$('recipient').value;try{$('send-error').textContent='';$('send-status').textContent='';await api('/api/messages',{method:'POST',body:JSON.stringify({meeting_id:current.id,text:$('text').value,recipient,kind:'talk',client_id:crypto.randomUUID()})});$('text').value='';$('recipient').value='all';await refresh();}catch(e){$('send-error').textContent=e.message;}};
$('text').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing&&event.keyCode!==229){event.preventDefault();$('send').click();}});
$('pause').onclick=()=>control(current.status==='paused'?'resume':'pause'); $('end').onclick=()=>confirm(t('endConfirm'))&&control('end');
async function control(action){try{$('control-error').textContent='';await api('/api/control',{method:'POST',body:JSON.stringify({meeting_id:current.id,action})});await refresh();}catch(e){$('control-error').textContent=e.message;}}
applyLanguage(); if(token){refresh();setInterval(refresh,1200);}
