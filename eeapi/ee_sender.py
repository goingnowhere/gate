#!/usr/bin/env python3

import csv
import math
import mysql.connector
import time
import smtplib
from email.message import EmailMessage

cnx = mysql.connector.connect(
  host="172.20.1.10",
  user="ee",
  password="<redacted>",
  database="nowhere_ee"
)

def set_alloc(tid, al):
  sql = ("INSERT INTO allocations(Team, Date, Allocation) VALUES(%s, '2022-06-29', %s)")

  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (tid, al))
  cnx.commit()
  cursor.close()
 
  return(1)

def add_to_db(team):
  sql = ("INSERT INTO teams(Teamname, Type) VALUES(%s, 2)")
 
  cursor = cnx.cursor(buffered=True)
  cursor.execute(sql, (team, ))
  cnx.commit()
  tid = cursor.lastrowid
  cursor.close()
 
  return(tid)

with open('/tmp/b.csv') as csvfile:
  breader = csv.reader(csvfile)
  for r in breader:


    alloc = int(math.ceil(int(r[28]) * 0.25))
    print("1st: {} 2nd: {} alloc: {}".format(r[1], r[28], alloc))

    msg = EmailMessage()

    mbody = """
Dear Barrio Lead

Firstly, apologies over the late running of Early Entry this year. In 2019 after Nowhere we had a server crash, and it wasn't noticed that the EE system was one of the casualties until it was time to spin it up this year. The effort to rebuild it took longer than expected and isn't finished yet. Maybe next year. Instead of the usual system where we emailed you a login and you entered your members, we need you to email us a list of the ticket references of your members which we will then enter into the system manually.

{} has {} EE spaces allocated to it, so if you could reply to this email with them listed one below the other we will get them processed and your EE tickets sent. Example:
QTK335535
QTK595634
QTK456576

If you have any queries about the Early Entry system, please email earlyentry@goingnowhere.org and we'll try help.

Regards

Bruce (and the rest of the Early Entry team)
""".format(r[2], alloc)

    msg['Subject'] = f'Nowhere 2022 Early Entry for {r[2]}'
    msg['From'] = 'earlyentry@goingnowhere.org'
    msg['To'] = r[1]
    msg.set_content(mbody)

    s = smtplib.SMTP('darkhorse.euroburners.net', 587)
    s.send_message(msg)
    s.quit()

    teamid = add_to_db(r[2])
    set_alloc(teamid, alloc)
    time.sleep(2)

