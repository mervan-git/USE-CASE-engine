import tempfile,unittest,json
from pathlib import Path
import service as s
class Core(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=s.DATA;s.DATA=Path(self.temp.name);s.init()
 def tearDown(self):s.DATA=self.old;self.temp.cleanup()
 def test_bad_times(self):
  self.assertEqual(s.valid_clips([{'start_seconds':-1,'end_seconds':6},{'start_seconds':2,'end_seconds':float('nan')},{'start_seconds':8,'end_seconds':20}],4,8),[])
 def test_duplicates(self):
  r=s.start('snijders');c={'start_seconds':30,'end_seconds':36,'description_nl':'test'}
  self.assertTrue(s.add_clip('snijders',r,'abcdefghijk','test',c));self.assertFalse(s.add_clip('snijders',r,'abcdefghijk','test',c))
  self.assertFalse(s.add_clip('snijders',r,'abcdefghijk','test',{**c,'start_seconds':60,'end_seconds':66}))
 def test_job_idempotency(self):self.assertEqual(s.start('snijders'),s.start('snijders'))
 def test_usage(self):
  self.assertIsNone(s.usage_cost({}));self.assertAlmostEqual(s.usage_cost({'total_input_tokens':1000,'total_output_tokens':100,'total_thought_tokens':100}),.0015)
 def test_unknown_cost_blocks(self):
  r=s.start('snijders');s.execute('INSERT INTO calls VALUES(?,?,?,?,?,?,?,?,?)',(s.uid(),r,'gemini','test','','timeout','{}',None,0))
  with self.assertRaises(s.Halt):s.Research(r).check()
 def test_public_url(self):
  with self.assertRaises(ValueError):s.safe_url('http://127.0.0.1/')
 def test_query_duration(self):self.assertEqual(s.duration_seconds('PT1M30S'),90)
 def test_cached_full_pipeline(self):
  r=s.start('snijders');research=s.Research(r)
  research.website=lambda:''
  def ai(prompt,media=None,purpose='planning',vid=''):
   if purpose=='planning':return {'brief':'window washing','queries':['window cleaning']}
   return {'clips':[{'start_seconds':20,'end_seconds':26,'description_nl':'Wassen'},{'start_seconds':30,'end_seconds':36,'description_nl':'Wassen'}]}
  def api(url,provider,purpose,payload=None,vid=''):
   if purpose=='search.list':return {'items':[{'id':{'videoId':'abcdefghijk'},'snippet':{'title':'Cleaning'}}]}
   return {'items':[{'id':'abcdefghijk','contentDetails':{'duration':'PT50S'}}]}
  research.ai=ai;research.api=api
  count,_=research.work();self.assertEqual(count,1)
  count,_=research.work();self.assertEqual(count,0)
 def test_autonomous_no_client_needed(self):
  from unittest.mock import patch
  with patch.object(s,'keys',return_value={'YOUTUBE_API_KEY':'test','GEMINI_API_KEY':'test'}):s.discovery_tick()
  r=s.one("SELECT * FROM runs WHERE client='__library__'")
  self.assertIsNotNone(r)
  self.assertTrue(json.loads(r['config'])['discovery'])
  self.assertEqual(s.start_discovery(),r['id'])
 def test_pause_cancels_queued(self):
  r=s.start_discovery();s.save_auto({'enabled':False})
  self.assertEqual(s.one('SELECT status FROM runs WHERE id=?',(r,))['status'],'cancelled')
  with self.assertRaises(ValueError):s.start_discovery()
 def test_tag_validation(self):
  clips=s.valid_clips([{'start_seconds':0,'end_seconds':6,'action':'Fietsen','camera':'Tracking / volgen'}],4,12)
  self.assertEqual(clips[0]['action'],'Fietsen')
  clips=s.valid_clips([{'start_seconds':0,'end_seconds':6,'action':'Made up','camera':'Imaginary'}],4,12)
  self.assertEqual(clips[0]['camera'],'Onbekend')
 def test_global_duplicates(self):
  r=s.start_discovery();clip={'start_seconds':30,'end_seconds':36,'description_nl':'test','action':'Handwerk','camera':'Statisch'}
  self.assertTrue(s.add_clip('snijders',r,'newvideo123','test',clip))
  self.assertFalse(s.add_clip('__library__',r,'newvideo123','test',clip))
 def test_daily_budget_blocks(self):
  r=s.start_discovery();s.execute('INSERT INTO calls VALUES(?,?,?,?,?,?,?,?,?)',(s.uid(),r,'gemini','test','','completed','{}',.30,s.time.time()))
  with self.assertRaises(s.Halt):s.Research(r).check()
 def test_customer_can_find_global_video(self):
  r=s.start_discovery();c={'start_seconds':40,'end_seconds':46,'description_nl':'test'}
  self.assertTrue(s.add_clip('__library__',r,'casevideo12','test',c))
  self.assertIsNone(s.known_video('snijders','casevideo12'))
  self.assertTrue(s.add_clip('snijders',r,'casevideo12','test',c))
  self.assertFalse(s.add_clip('snijders',r,'casevideo12','test',c))
 def test_ranking_relevance_cost_and_availability(self):
  items=[{'id':{'videoId':v},'snippet':{'title':title}} for v,title in [('long','window cleaning'),('short','window cleaning'),('irrelevant','cooking'),('private','window cleaning')]]
  meta={v:{'contentDetails':{'duration':dur}} for v,dur in [('long','PT9M'),('short','PT1M'),('irrelevant','PT30S'),('private','PT1M')]}
  meta['private']['status']={'privacyStatus':'private'}
  self.assertEqual([x['id']['videoId'] for x in s.rank_candidates(items,meta,'window cleaning',4)],['short','long','irrelevant'])
 def test_discovery_prompt_requires_selected_action(self):
  r=s.start_discovery();research=s.Research(r);prompts=[]
  def api(url,provider,purpose,payload=None,vid=''):
   if purpose=='search.list':return {'items':[{'id':{'videoId':'abcdefghijk'},'snippet':{'title':'person walking'}}]}
   return {'items':[{'id':'abcdefghijk','contentDetails':{'duration':'PT50S'}}]}
  def ai(prompt,*args):prompts.append(prompt);return {'clips':[]}
  research.api=api;research.ai=ai;research.work()
  self.assertIn('Required action category: '+research.c['lane'],prompts[0])
 def test_rate_limit_recovers_and_records_rejection(self):
  from unittest.mock import patch
  import io,urllib.error
  r=s.start('snijders');research=s.Research(r);research.k={'GEMINI_API_KEY':'test'}
  error=urllib.error.HTTPError('https://example.com',429,'limit',{},io.BytesIO(b'{"error":{"details":[{"retryDelay":"0s"}]}}'))
  response=io.BytesIO(b'{"usage":{"total_input_tokens":1,"total_output_tokens":1,"total_thought_tokens":0}}')
  with patch.object(s.urllib.request,'urlopen',side_effect=[error,response]) as request,patch.object(s.time,'monotonic',side_effect=[0,16]):
   research.api('https://example.com','gemini','planning')
  self.assertEqual(request.call_count,2)
  calls=s.rows('SELECT * FROM calls WHERE run=?',(r,))
  self.assertEqual(calls[0]['cost'],0)
  self.assertEqual(calls[0]['status'],'HTTP 429 rejected')
 def test_rate_limit_bounded_and_hard_quota(self):
  from unittest.mock import patch
  research=s.Research(s.start('snijders'))
  with patch.object(research,'api_once',side_effect=s.RateLimit(0)) as call,patch.object(s.time,'monotonic',side_effect=[0,16,20,51]):
   with self.assertRaisesRegex(s.Halt,'blijft actief'):research.api('x','gemini','planning')
   self.assertEqual(call.call_count,3)
  with patch.object(research,'api_once',side_effect=s.RateLimit(0,True)) as call:
   with self.assertRaisesRegex(s.Halt,'factureringslimiet'):research.api('x','gemini','planning')
   self.assertEqual(call.call_count,1)
 def test_rate_limit_wait_can_be_cancelled(self):
  from unittest.mock import patch
  r=s.start('snijders');research=s.Research(r)
  s.execute("UPDATE runs SET status='cancelled' WHERE id=?",(r,))
  with patch.object(research,'api_once',side_effect=s.RateLimit(30)),patch.object(s.time,'monotonic',return_value=0):
   with self.assertRaisesRegex(s.Halt,'Gestopt'):research.api('x','gemini','planning')
 def test_generic_billing_advice_is_not_hard_quota(self):
  import io,urllib.error
  def error(body):return urllib.error.HTTPError('https://example.com',429,'limit',{},io.BytesIO(json.dumps(body).encode()))
  delay,hard=s.rate_limit_info(error({'error':{'message':'Check your plan and billing details','details':[{'retryDelay':'20s'}]}}))
  self.assertEqual(delay,20);self.assertFalse(hard)
  _,hard=s.rate_limit_info(error({'error':{'details':[{'quotaId':'RequestsPerDay'}]}}))
  self.assertTrue(hard)
if __name__=='__main__':unittest.main()
