#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

from __future__ import unicode_literals

import os
import time
import threading
import json

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import sync


class LocalEventHandler(FileSystemEventHandler):
    def __init__(self, tahoe, local_dir, remote_dircap):
        self.tahoe = tahoe
        self.local_dir = local_dir
        self.remote_dircap = remote_dircap
        if not os.path.isdir(self.local_dir):
            os.makedirs(self.local_dir)
        self.do_backup = False
        self.check_for_backup()

    def on_modified(self, event):
        self.do_backup = True
        print(event)

    def check_for_backup(self):
        if self.do_backup:
            self.do_backup = False
            time.sleep(1)
            if not self.do_backup:
                self.tahoe.backup(self.local_dir, self.remote_dircap)
        t = threading.Timer(1.0, self.check_for_backup)
        t.setDaemon(True)
        t.start()

#XXX Combine these two classes?

class Watcher():
    def __init__(self, parent, tahoe, local_dir, remote_dircap, polling_frequency=60):
        self.parent = parent
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        if not os.path.isdir(self.local_dir):
            os.makedirs(self.local_dir)
        self.polling_frequency = polling_frequency
        self.latest_snapshot = 0

    def start(self):
        #self.sync()
        self.check_for_updates()
        print("*** Starting observer in %s" % self.local_dir)
        event_handler = LocalEventHandler(self.tahoe, self.local_dir, self.remote_dircap)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.local_dir, recursive=True)
        self.observer.start()

    def stop(self):
        print("*** Stopping observer in %s" % self.local_dir)
        try:
            self.observer.stop()
            self.observer.join()
        except:
            pass

    def check_for_updates(self):
        latest_snapshot = self.get_latest_snapshot()
        if latest_snapshot == self.latest_snapshot:
            print("Up to date ({}); nothing to do.".format(latest_snapshot))
        else:
            print("New snapshot available ({}); syncing...".format(latest_snapshot))
            
            self.parent.sync_state += 1
            print "@@@@@@@@ sync state is: " +str(self.parent.sync_state)
            sync.sync(self.tahoe, self.local_dir, self.remote_dircap)
            self.parent.sync_state -= 1
            print "@@@@@@@@ sync state is NOW: " +str(self.parent.sync_state)

            self.latest_snapshot = latest_snapshot
        t = threading.Timer(self.polling_frequency, self.check_for_updates)
        t.setDaemon(True)
        t.start()

    def get_latest_snapshot(self):
        dircap = self.remote_dircap + "/Archives"
        out = self.tahoe.command_output("ls --json %s" % dircap)
        j = json.loads(out)
        snapshots = []
        for snapshot in j[1]['children']:
            snapshots.append(snapshot)
        snapshots.sort()
        return snapshots[-1:][0]
        #latest = snapshots[-1:][0]
        #return utils.utc_to_epoch(latest) 

