"""Durable relay delivery claims; source brokers remain decision authorities."""
import sqlite3,time,json


def due(created,now,parent_seen=None):
    if not 0<=now-created<900:return False
    return now-created>=180 or (parent_seen is not None and now-parent_seen>60)


class Pending:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS cards(kind TEXT,id TEXT,payload TEXT,state TEXT,message TEXT,PRIMARY KEY(kind,id))')
        self.db.commit()

    def claim(self,kind,identifier,payload):
        with self.db:
            result=self.db.execute('INSERT OR IGNORE INTO cards VALUES(?,?,?,\'sending\',NULL)',(kind,identifier,json.dumps(payload)))
        return result.rowcount==1

    def sent(self,kind,identifier,message):
        with self.db:self.db.execute('UPDATE cards SET state=\'sent\',message=? WHERE kind=? AND id=?',(str(message),kind,identifier))

    def load(self,kind,identifier):
        row=self.db.execute('SELECT payload,state,message FROM cards WHERE kind=? AND id=?',(kind,identifier)).fetchone()
        return (json.loads(row[0]),row[1],row[2]) if row else None

    def finish(self,kind,identifier,state):
        with self.db:self.db.execute('UPDATE cards SET state=? WHERE kind=? AND id=?',(state,kind,identifier))
