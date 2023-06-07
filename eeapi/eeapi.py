#!/bin/env python3

import cherrypy
import mysql.connector
import mysql.connector.pooling
import yaml
import json
import pprint
import hashlib
import requests
import time
import re
import string
from random import choice, randint
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfFileWriter
from io import BytesIO

## global vars
cfgfile = 'config.yml'
config = {}
cnx = ''
ee_template = '/usr/src/app/templates/EE_2023_template.png'
smtp_server = 'darkhorse.euroburners.net'
year = 2023

SESSION_TIME_LIMIT = 600
CACHE_LIMIT = 9


def load_config(cfgfile):
  with open(cfgfile, "r") as stream:
    cfg = yaml.safe_load(stream)
  return(cfg)

def send_ticket(cnx, tic):
  tdets = get_ticket_details(cnx, tic)
  pdf = generate_pdf(cnx, tic, tdets)

  msg = EmailMessage()
  msg['Subject'] = "Nowhere {} Early Entry - QTK{}".format(year, tic)
  msg['From'] = formataddr(('Nowhere Early Entry', 'earlyentry@goingnowhere.org'))
  msg['To'] = formataddr((tdets['Name'], tdets['Email']))
  msg.set_content("Your Nowhere {} Early Entry ticket is attached. This allows you early entry from the date on the ticket. It's always a good idea to print this out to have ready for scanning at gate ".format(year))

  ## read in pdf and attach
  #with open(attachment, 'rb') as pdf:
    #content = pdf.reda()
  #msg.add_attachment(attachment, 'rb').read(), maintype='application', subtype='pdf', filename='ee.pdf')
  msg.add_attachment(pdf, maintype='application', subtype='pdf', filename='Nowhere_QTK' + tic + '_ee.pdf')
  
  smtps =  smtplib.SMTP(smtp_server ,587)
  smtps.send_message(msg)

  
def adduser(cnx, team, dept, email):

  allchar = string.ascii_letters + string.digits
  rand_key = "".join(choice(allchar) for x in range(randint(12,12)))
  sql = "INSERT INTO users(Email, Dept, Team, Akey, Level) VALUES(%s, %s, %s, %s, 1)"

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (email, dept, team, rand_key))

  uid = cursor.lastrowid
  cnx.commit()
  cursor.close()
  seckey = get_user_key(cnx, uid)
  ans = {'uid': uid, 'key': seckey}
  return(ans)

def get_user_key(cnx, uid):
  ans = ''
  sql = ("SELECT SHA2(CONCAT(Akey,Id, %s), 256) AS Seckey FROM users WHERE Id = %s")
  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (config['keyword'],uid))
  for y in cursor:
    ans = y[0]

  cursor.close()
  return(ans)

def create_team(cnx, team, dept):

  sql = "INSERT INTO teams(Teamname, Dept) VALUES(%s, %s)"

  cursor = cnx.cursor(buffered=True)
  print(team, dept)
  cursor.execute(sql, (team, dept))
  tid = cursor.lastrowid
  cnx.commit()
  cursor.close()

  return(tid)

def add_allocation(cnx, tid, date, alloc):
  sql = "INSERT INTO allocations(Allocation, Team, Date) VALUES(%s, %s, %s)"
  checka = get_team_allocations(cnx, tid)
  for a in checka:
    if checka[a]['Date'] == date:
      sql = "UPDATE allocations SET Allocation = %s WHERE Team = %s AND Date = %s"
      continue;

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (alloc, tid, date))
  cnx.commit()
  cursor.close()

  return(1)

def get_tids_emails(cnx, uid):
  ans = {}
  access = get_access(cnx, uid)
  if access['Level'] == 0 and access['Dept'] == 0:    #super user
    pass
  else:
    return()

  sql = "SELECT DISTINCT(Ticket) FROM tickets"

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql,)
  for x in cursor:
    tid = x[0]
    dets = get_tickets(cnx, tid, 'int')
    if not dets:
      print("{} is missing details in Quicket".format(tid))
      continue
    ans[dets[0]['Email']] = tid
  cursor.close()

  return(ans)
    
def generate_pdf(cnx, tic, tdets):
    teamdets = get_team_dept(cnx, tic)

    buffer = BytesIO()
    can = canvas.Canvas(buffer, pagesize=A4)
    can.drawImage(ee_template, 0, 0, width=595, height=843)

    ## barcode
    bcode = get_barcode(tic)
    barcode = code128.Code128(str(bcode), barWidth=0.6*mm, barHeight=12*mm)
    barcode.drawOn(can, 183, 135)

    ## Barcode text
    can.setFont('Courier', 12)
    can.drawString(455, 638, str(bcode))

    ## Team
    can.setFont('Times-BoldItalic', 16)
    can.drawString(105, 255, teamdets['Teamname'])

    ## Person
    can.setFont('Times-BoldItalic', 16)
    can.drawString(275, 303, tdets['Name'])

    ## E date
    can.setFont('Times-BoldItalic', 16)
    can.drawString(240, 279, tdets['Date'])

    ## Ticket ID
    can.setFont('Times-BoldItalic', 16)
    can.drawString(85, 232, "QTK{}".format(tic))

    can.showPage()
    can.save()
    
    tpdf = buffer.getvalue()
    buffer.close()
    return(tpdf)

def get_teams_from_uid(cnx, uid):
  dets = {}
  cursor = cnx.cursor(buffered=True, dictionary=True)
  access = get_access(cnx, uid) ## EG
  
  if access['Level'] == 0 and access['Dept'] == 0:    #super user
    sql = ("SELECT teams.Id, teams.Teamname AS TEAM, teams.Dept FROM teams")
    cursor.execute(sql,)

  elif access['Level'] == 0 and access['Dept'] != 0:   ##dept admin
    sql = ("SELECT teams.Id, teams.Teamname AS TEAM, teams.Dept FROM teams WHERE teams.Dept = %s")
    cursor.execute(sql,(access['Dept']))

  else:   ## ordinary user with one team
    sql = ("SELECT teams.Id, teams.Teamname AS TEAM, teams.Dept FROM teams WHERE teams.Id = %s")
    cursor.execute(sql,(access['Team']))

  for x in cursor:
    dets[x['Id']] = x
  cursor.close()

  return(dets)

def get_team_details(cnx, team):
  dets={}
  sql = ("SELECT teams.Id , teams.Teamname AS Team, Dept FROM teams WHERE Id = %s")

  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (team,))
  for x in cursor:
    dets = x

  cursor.close()
  
  dets['Allocations'] = get_team_allocations(cnx, team)
  return(dets)

def get_team_allocations(cnx, team):
  alocs = {}
  sql = ("SELECT Id, DATE_FORMAT(Date, \"%Y-%m-%d\") AS Date, Allocation FROM allocations WHERE Team = %s ORDER BY Date")
  counter = 0
  
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (team,))
  for x in cursor:
    alocs[counter] = x
    alocs[counter]['Allocated'] = get_team_ees(cnx, x['Id'])
    counter += 1

  cursor.close()
  return(alocs)


def get_barcode(tic):
  url = "https://fistbump.goingnowhere.org/noosethenooner?key={}&tid={}".format(config['fistbump']['key'], tic)
  response = requests.request("GET", url)
  bcode = json.loads(response.text)

  return(bcode)

def bump_fistbump():
  url = "https://fistbump.goingnowhere.org/cachepurge?key={}".format(config['fistbump']['key'])
  response = requests.request("GET", url)
  res = json.loads(response.text)

  return(res)


def get_names():
  names = {}
  url = "https://fistbump.goingnowhere.org/listnames?key={}".format(config['fistbump']['key'])
  response = requests.request("GET", url)
  rawdata =  json.loads(response.text)
  for n in rawdata:
    names['QTK' + str(n)] = rawdata[n]

  return(names)

def get_stats(cnx):
  s = {}
  sql = "SELECT COUNT(tickets.Id) AS tot, allocations.Date FROM tickets LEFT JOIN allocations ON tickets.Allocation = allocations.Id GROUP BY Date"
  
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql,)
  for x in cursor:
    s[str(x['Date'])] = x['tot']
  cursor.close()
  return(s)


def get_team_ees(cnx, aloc):
  tkts = {}
  sql = ("SELECT Id, Ticket, (UNIX_TIMESTAMP() - UNIX_TIMESTAMP(Added)) AS Added FROM tickets WHERE Allocation = %s")

  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (aloc,))
  for x in cursor:
    tkts[x['Id']] = {}
    url = "https://fistbump.goingnowhere.org/huntthenooner?key={}&nooner={}".format(config['fistbump']['key'], x['Ticket'])
    response = requests.request("GET", url)
    rdj = json.loads(response.text)
    if len(rdj) == 0:
      tkts[x['Id']]['Name'] = 'NOT VALID TICKET'
      continue
    if 'Name' in rdj[0]:
      tkts[x['Id']]['Name'] = rdj[0]['Name']
    else:
      tkts[x['Id']]['Name'] = 'NO NAME'
    tkts[x['Id']]['Add_lag'] = x['Added']

  cursor.close()
  return(tkts)

def check_login(cnx, un, key):
  dets = {}
  #sql = ("SELECT Id, Dept, Level FROM users WHERE Email = %s AND Akey = %s")   ## original user/pass
  sql = ("SELECT Id, Dept, Level FROM users WHERE Id = %s AND SHA2(CONCAT(Akey,Id, %s), 256)  = %s")
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (un, config['keyword'], key))
  for y in cursor:
    dets = y

  cursor.close()
  return(dets)

def get_session(cnx, uid):
  ses = {}
  sql = ("SELECT DATE_FORMAT(Started, \"%Y-%m-%d\") AS Started, Session FROM sessions WHERE User = %s");
 
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (uid,) )

  for x in cursor:
    ses = x

  cursor.close()
  return(ses)

def session(cnx, uid, apkey):
  cses = get_session(cnx, uid)
  allchar = string.ascii_letters + string.digits
  saltyseed = "".join(choice(allchar) for x in range(randint(6,6)))

  cursor = cnx.cursor(buffered=True)
  ## already have a session
  if 'Session' in cses:
    sql = ("UPDATE sessions SET Session = SHA2(CONCAT(%s, %s), 512), Salt = %s, Started = NOW() WHERE User = %s")
    cursor.execute(sql, (saltyseed, apkey, saltyseed, uid))

  ## new session
  else:
    sql = ("INSERT INTO sessions(User, Salt, Session) VALUES (%s, %s, SHA2(CONCAT(%s, %s), 512))")
    cursor.execute(sql, (uid, saltyseed, saltyseed, apkey))
  
  cnx.commit()
  cursor.close()

  ses = get_session(cnx, uid)
  return(ses['Session'])
  
def get_access(cnx, uid):
  ans = {}
  sql = ("SELECT Team, Level, Dept FROM users WHERE Id = %s")
  
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (uid,))
  for x in cursor:
    ans = x
  cursor.close()

  return(ans)

def team_alloc(cnx, uid, tid):
  dets = get_team_details(cnx, tid)
  access = get_access(cnx, uid)
  if access['Level'] == 0:
    ## super user with all depts
    if access['Dept'] == 0:
      pass
    elif access['Dept'] == dets['Dept']:
      pass
    else:
      return()
  elif int(tid) == access['Team']:
    pass
  else:
    return()
  return(dets)

def uid_teams(cnx, uid, dept):
  teams = []
  access = get_access(cnx, uid)
  ## super user
  if access['Level'] == 0:
    ## super user with all depts
    if access['Dept'] == 0 and dept != 0:
      sql = ("SELECT Id FROM teams WHERE Dept = {} ORDER BY Teamname".format(dept))
    ## super user with single depts
    else:
      sql = ("SELECT Id FROM teams WHERE Dept = {} ORDER BY Teamname".format(access['Dept']))
  
  ## normal user
  else:
    team = get_teamid(cnx, uid)
    teams.append(get_team_details(cnx, team))
    return(teams)
  
  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql,)
  for y in cursor:
    teams.append(get_team_details(cnx, y[0]))
  cursor.close()
  
  return(teams)

def get_teamid(cnx, uid):
  t = None
  sql = ("SELECT Team FROM users WHERE Id = %s")

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (uid, ))
  for y in cursor:
    t = y[0]
  cursor.close()

  return(t)

def get_team_dept(cnx, tic):
  dets = {}
  sql = ("SELECT teams.Teamname, teams.Dept FROM teams, allocations, tickets WHERE tickets.Allocation = allocations.Id AND allocations.Team = teams.Id AND tickets.Ticket = %s")
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (tic,))
  for y in cursor:
    dets = y
  cursor.close()

  return(dets)

def uid_from_session(cnx, ses):
  uid = None
  sql = ("SELECT User FROM sessions WHERE Session = %s")
  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (ses,))
  for y in cursor:
    uid = y[0]
  cursor.close()

  return(uid)

def log(cnx, action):
  cursor = cnx.cursor(buffered=True)
  if 'tkt' in action:
    sql = ("INSERT INTO logs(User, Action, Ticket) VALUES (%s, %s, %s)")
    uid = uid_from_session(cnx, action['session'])
    cursor.execute(sql, (uid, action['action'], action['tkt']))
  elif 'user' in action:
    sql = ("INSERT INTO logs(User, Action) VALUES (%s, %s)")
    cursor.execute(sql, (action['user'], action['action']))
  else:
    sql = ("INSERT INTO logs(Action) VALUES (%s)")
    cursor.execute(sql, (action['action'],))

  cnx.commit()
  cursor.close()

  return(1)

def uid_dept(cnx, uid):
  sql = ("SELECT Dept from user WHERE Id = %s")

  cursor = cnx.curosr(buffered=True)
  cursor.execute(sql, (uid,))
  for y in cursor:
    t = y[0]
  cursor.close()

  return(t)

def get_ticket_details(cnx, ref):
  raw = get_tickets(cnx, ref, 'int')
  dets = {}
  for t in raw:
    dets = t

  sql = ("SELECT teams.Teamname AS Team, DATE_FORMAT(allocations.Date, \"%Y-%m-%d\") AS Date FROM allocations, tickets, teams  WHERE tickets.Allocation = allocations.Id AND teams.Id = allocations.Team AND tickets.Ticket = %s")
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (ref,))
  for x in cursor:
   dets['Date'] = x['Date']
   dets['Team'] = x['Team']
  cursor.close()

  return(dets)
    
def get_tickets(cnx, ref, dest):
  url = "https://fistbump.goingnowhere.org/huntthenooner?key={}&nooner={}".format(config['fistbump']['key'], ref)
  response = requests.request("GET", url)
  rdj = json.loads(response.text)
  res = []
  for t in rdj:
    tres = {}
    tres['Name'] = t['Name']
    tres['TicketId'] = t['TicketId']
    if dest == 'int':
      tres['Email'] = t['Email']
    res.append(tres)
  return(res)

def get_alloc_dets(cnx, alloc):
  ans = {}

  sql = ("SELECT allocations.Id, allocations.Team, allocations.Date, allocations.Allocation, teams.Dept FROM allocations, teams  WHERE allocations.Team = teams.Id AND allocations.Id = %s")
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (alloc,))
  for x in cursor:
    ans = x
  cursor.close()

  return(ans)

def get_allocation_used(cnx, alloc):
  ans = 0
  sql = ("SELECT COUNT(Allocation) FROM tickets WHERE Allocation = %s")
  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (alloc,))
  for y in cursor:
    ans = y[0]
  cursor.close()

  return(ans)

def assign_tkt(cnx, alloc, ticket, uid):
  ## retrieve allocation
  m = re.match('^e_(\d+)_\d+$', alloc)
  if m:
   realal = m.group(1)
  else:
   return(0)
  
  alloc_id = int(realal)

  access = get_access(cnx, uid) ## EG
  team = get_teamid(cnx, uid)
  alloc_dets = get_alloc_dets(cnx, alloc_id)
  used_allocs = get_allocation_used(cnx, alloc_id)
  
  ## do we have space
  if used_allocs >= alloc_dets['Allocation']:
    return({'state': 'failed', 'reason': 'over allocation - naughty naughty'})

  ## are we allowed to add tickets to this team
  if access['Level'] == 0 and access['Dept'] == 0:    #super user
    pass
  elif access['Level'] == 0 and access['Dept'] == alloc_dets['Dept']:  ## power user
    pass
  elif team == alloc_dets['Team']:
    pass
  else:
    return({'state': 'fail', 'reason': 'access level'})

  ## Is this ticket already assigned elsewhere - for an earlier EE
  ee_tic = get_ticket_details(cnx, ticket)
  if 'Team' in ee_tic:
    return({'state': 'failed', 'reason': "{} already has EE with {}".format( ee_tic['Name'], ee_tic['Team']), 'Team': alloc_dets['Team'], 'team': alloc_dets['Team']})

  sql =("INSERT INTO tickets(Ticket, Allocation) VALUES(%s, %s)")

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql,(ticket, alloc_id))
  cnx.commit()
  id = cursor.lastrowid
  cursor.close()

  return({'state': 'success', 'tref': id, 'team': alloc_dets['Team'], 'Team': alloc_dets['Team']})

def quicket_checkin(cnx):
  cacha = []
  cons = {}
  cons['productId'] = config['quicket']['product_id']
  cons['scannerPin'] = config['quicket']['scanner_pin']
  cons['scannerName'] = config['quicket']['scanner']

  ## get current cache
  sql = "SELECT Ticket, UNIX_TIMESTAMP(Created) AS Ut FROM checked_in"
  sqldel = "DELETE FROM checked_in WHERE Ticket = %s"

  
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql,)
  for y in cursor:
    d = {}
    d['c'] = True
    d['cd'] = str(y['Ut'] * 1000)
    d['ti'] = y['Ticket']
    d['no'] = ''
    cacha.append(d)


  cons['data'] = cacha
  ## checkin at quicket
  url = 'https://www.quicket.co.za/webservices/ProductService.svc/ScannerPushRequest'
  response = requests.request("POST", url, json = cons)
  ans = json.loads(response.text)

  if ans['ScannerPushRequestResult'] == 'success':
    ## delete tickets from cache
    for t in cacha:
      cursor.execute(sqldel, (t['ti'],))
    cnx.commit()
    cursor.close()
  else:
    pprint.pprint(ans)

   
def get_ee_ticket_details(cnx, ticket_id):
  ans = {}
  sql = ("SELECT tickets.Id, tickets.Ticket, tickets.Allocation, tickets.Added, allocations.Team, allocations.Date FROM tickets, allocations WHERE tickets.Allocation = allocations.Id AND tickets.Id = %s")
  cursor = cnx.cursor(buffered=True, dictionary=True)
  cursor.execute(sql, (ticket_id,))
  for x in cursor:
    ans = x
  cursor.close()

  return(ans)

def cancel_ee(cnx, ee, uid):

  print(ee)
  m = re.match('^ca_(\d+)$', ee)
  if m:
    realee = m.group(1)
  else:
    return(0)
  realee = int(realee)

  access = get_access(cnx, uid)
  ee_tic_dets = get_ee_ticket_details(cnx, realee)
  pprint.pprint(ee_tic_dets)
  ticket_team_dets = get_team_dept(cnx, ee_tic_dets['Ticket'])
  
  if access['Level'] == 0:
    ## super user with all depts
    if access['Dept'] == 0:
      pass
    elif access['Dept'] == ticket_team_dets['Dept']:
      pass
  elif ee_tic_dets['Team'] == access['Team']:
    pass
  else:
    return({'state': 'failed', 'reason': 'Access level insufficient to delete ticket'})

  sql = ("DELETE FROM tickets WHERE Id = %s")

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (realee,))
  cnx.commit()
  cursor.close()

  return({'state': 'success', 'ticket': ee_tic_dets['Ticket'], 'allocation': ee_tic_dets['Allocation']})

def cache_count(cnx):
  sql = "SELECT COUNT(Ticket) FROM checked_in"

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql,)
  for y in cursor:
    c = y[0]
  cursor.close()

  return(c)

def barcode_state(cnx, bcode):

  if not bcode.isnumeric():
    return()

  ## check Quicket state
  args = {'key': config['fistbump']['key'], 'barcode': bcode}
  url = 'https://fistbump.goingnowhere.org/beepbeep'
  response = requests.request("POST", url, data = args)
  if response.text is None:
    return()
  qstate = json.loads(response.text)

  sql = "SELECT Barcode, Created FROM checked_in WHERE Barcode = %s"
  ## check if it's in the checked in cache
  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (bcode, ))
  for x in cursor:
    qstate['CI'] = 'Yes'
    qstate['CIdate'] = str(x[1])
  cursor.close()

  return(qstate)

def ci_stats():
  args = {'key': config['fistbump']['key']}
  url = 'https://fistbump.goingnowhere.org/stats'
  response = requests.request("POST", url, data = args)
 
  cstats = json.loads(response.text)
  return(cstats)
  
def check_in(cnx, bcode):
  sql = "INSERT INTO checked_in(Barcode, Ticket) VALUES(%s, %s)"
  
  prei = barcode_state(cnx, bcode)
  if 'CI' not in prei:
    return('UNDEF')
  elif prei['CI'] == 'Yes':
    return('EXISTING')

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (bcode, prei['TID']))
  cnx.commit()
  cursor.close()

  posti = barcode_state(cnx, bcode)
  if 'CI' not in posti:
    return('FAIL')
  elif posti['CI'] == 'Yes':
    return('CHECKEDIN')
  return('FAIL')

def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"

class ManglerAPI(object):
  @cherrypy.expose
  def index(self):
    return "YOUR REQUEST WAS NOT UNDERSTOOD!"

  ## LOGIN
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def login(self, uid, key):
    cnx = cnxpool.get_connection()
    print(uid, key)
    u_dets = check_login(cnx, uid, key)

    pprint.pprint(u_dets)
    if 'Id' in u_dets:
      ses = session(cnx, u_dets['Id'], key)
      dets = {'Uid': u_dets['Id'], 'Sesuuid': ses, 'Level': u_dets['Level'], 'Dept': u_dets['Dept']}
      action = {'user': u_dets['Id'], 'action': "{} logged in".format(uid)}
      log(cnx, action)
      cnx.close()
      return(dets)

    else:
      action = {'action': "{} attempted to log in from {}".format(uid, cherrypy.request.headers['X-Real-Ip'])}
      log(cnx, action)
      cnx.close()
      return()

  ## TEAM ALLOCATIONS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def allocations(self, session, dept=0, raw = None):
    cnx = cnxpool.get_connection()
    uid = uid_from_session(cnx, session)
    if (session == 'nada') :
      uid = 1
    
    if not uid:
      cnx.close()
      return({'state': 'failed ses'})
    teams = uid_teams(cnx, uid, dept)
    cnx.close()
    return(teams)

  ## TEAM ALLOCATION - single
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def team_allocation(self, session, team):
    cnx = cnxpool.get_connection()
    print(session, team)
    uid = uid_from_session(cnx, session)
    if not uid:
      cnx.close()
      return({'state': 'failed ses'})
    team_dets = team_alloc(cnx, uid, team)
    cnx.close()
    return(team_dets)

  ## LIST TEAMS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def get_teams(self, session, raw = None):
    cnx = cnxpool.get_connection()
    uid = uid_from_session(cnx, session)
    if not uid:
      cnx.close()
      return()
    teams = get_teams_from_uid(cnx, uid)
    cnx.close()
    return(teams)

  ## GET TID's AND EMAILS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def tidemails(self, session):
    cnx = cnxpool.get_connection()
    uid = uid_from_session(cnx, session)
    if not uid:
      cnx.close()
      return()
    tidse = get_tids_emails(cnx, uid)
    cnx.close()
    return(tidse)

  ## SET TEAM/DATE ALLOCATION
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def set_allocation(self, session, team, date, alloc):
    cnx = cnxpool.get_connection()
    if session != 'nada':
      cnx.close()
      return()
    r = add_allocation(cnx, team, date, int(alloc))
    cnx.close()
    return(r)

  ## CREATE TEAM
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def add_team(self, session, team, dept):
    cnx = cnxpool.get_connection()
    cnx.set_charset_collation('utf8mb4', 'utf8mb4_general_ci')
    if session != 'nada':
      cnx.close()
      return()
    tuid = create_team(cnx, team, dept)
    cnx.close()
    return(tuid)

  ## ADD USER
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def add_user(self, session, team, dept, email):
    cnx = cnxpool.get_connection()
    if session != 'nada':
      cnx.close()
      return()
    userdets = adduser(cnx, team, dept, email)
    cnx.close()
    return(userdets)

  ## TICKET LOOKUPS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def ticket(self, session, ticket):
    cnx = cnxpool.get_connection()
    uid = uid_from_session(cnx, session)
    if not uid:
      cnx.close()
      return()
    tics = get_tickets(cnx, ticket, 'ext')
    cnx.close()
    return(tics)

  ## STATS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def stats(self, session):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    s = get_stats(cnx)
    cnx.close()
    return(s)

  ## NAME LIST
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def namelist(self, session):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    names = get_names()
    cnx.close()
    return(names)

  ## TICKET ASSIGN
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def assign_ticket(self, session, ticket, allocation):
    cnx = cnxpool.get_connection()
    uid = uid_from_session(cnx, session)
    if not uid:
      cnx.close()
      return()
    print(ticket, allocation, uid)
    res = assign_tkt(cnx, allocation, ticket, uid)
    pprint.pprint(res)
    if res['state'] == 'success':
      action = {'session': session, 'tkt': ticket, 'action': "Assigned to {}".format(allocation)}
      send_ticket(cnx, ticket)
    elif res['state'] == 'fail':
      action = {'session': session, 'tkt': ticket, 'action': "Failed to assign to {}".format(allocation)}
    else:
      action = {'session': session, 'tkt': ticket, 'action': "Failed to assign to {} - system error".format(allocation)}
    log(cnx, action)
    cnx.close()
    return(res)

  ## EE CANCEL
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def cancelee(self, session, eeid):
    cnx = cnxpool.get_connection()
    uid = uid_from_session(cnx, session)
    if not uid:
      cnx.close()
      return()
    res = cancel_ee(cnx, eeid, uid)
    pprint.pprint(res)
    if res['state'] == 'success':
      action = {'session': session, 'tkt': eeid, 'action': "{} in {} removed by {}".format(res['ticket'], res['allocation'], uid)}
    else:
      action = {'session': session, 'tkt': eeid, 'action': "Delete failed by {}".format(uid)}

    log(cnx, action)
    cnx.close()
    return(res)

  ## EE RESEND
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def eeresend(self, session, eeid):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    res = send_ticket(cnx, eeid)
    cnx.close()
    return(res)

  ## TICKET CHECKIN
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def checkin(self, session, barcode):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    res = check_in(cnx, barcode)
    cachecount = cache_count(cnx)
    if cachecount > CACHE_LIMIT:
      quicket_checkin(cnx)
    cnx.close()
    print(res, barcode)
    return(res)

  ## FLUSH CACHE
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def flushcache(self, session):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    cachecount = cache_count(cnx)
    if cachecount > 0:
      quicket_checkin(cnx)
    cnx.close()
    bump_fistbump()
    return('flushed')

  ## BARCODE DETAILS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def barcode(self, session, barcode):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    res = barcode_state(cnx, barcode)
    cnx.close()
    return(res)

  ## CHECKIN STATS
  @cherrypy.expose
  @cherrypy.tools.json_out()
  def cistats(self, session):
    access = check_access(session)
    cnx = cnxpool.get_connection()
    quicket_checkin(cnx)
    cnx.close()
    bump_fistbump()
    res = ci_stats()
    return(res)

  
if __name__ == '__main__':
  config = load_config(cfgfile)
  dbconfig = {
              'database': config['mariadb']['db'],
              'user': config['mariadb']['user'],
              'password': config['mariadb']['pass'],
              'host': config['mariadb']['host'],
              'charset': 'utf8mb4'
             }
  cnxpool = mysql.connector.pooling.MySQLConnectionPool(pool_name = "ee",
                                                    pool_size = 16,
                                                    **dbconfig)
  
  #cherrypy.config.update({'server.socket_port': 80})
  cherrypy.config.update({
                          'engine.autoreload.on': True,
                          'server.socket_host': '0.0.0.0',
                          'tools.CORS.on': True
                        })
  cconf = {'/': {'tools.CORS.on': True} }
  #cherrypy.tree.mount(Root(), config=cconfig)
  cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
  cherrypy.quickstart(ManglerAPI()) 
