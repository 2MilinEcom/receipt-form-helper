chrome.action.onClicked.addListener(tab => {
  const query = new URLSearchParams({tab: String(tab.id)});
  chrome.tabs.create({url: chrome.runtime.getURL('app.html') + '?' + query});
});
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message.type !== 'choices' || !sender.tab?.url?.startsWith('https://claims-center.americanexpress.com/')) return;
  fetch('http://127.0.0.1:18765/choices', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({labels:message.labels,target:message.target})})
    .then(async r=>{const data=await r.json();if(!r.ok)throw Error(data.error);return data;})
    .then(respond).catch(e=>respond({error:e.message}));
  return true;
});
