#!/usr/bin/env python
# encoding: utf-8

import threading
import datetime
import socket
import urllib2
import netifaces
import time
import psutil
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM
from flask import Flask, render_template, jsonify
from gevent.wsgi import WSGIServer
from gevent import monkey, sleep
from config import INTERVAL
import os
monkey.patch_all()

app = Flask(__name__)

app.config.from_object('config')

class StautsInfo(threading.Thread):

    def __init__(self, interval=INTERVAL):
        super(StautsInfo, self).__init__()
        self.event = threading.Event()
        self._interval = interval
        self._net = dict()

    def bytes2human(self, n):
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)
        return "%sB" % n


    def get_CPU_temp(self):
        with open('/sys/class/thermal/thermal_zone0/temp') as fp:
            cpu_temp = fp.read()
            return float(cpu_temp) / 1000

    def get_GPU_temp(self):
        res = os.popen('/opt/vc/bin/vcgencmd measure_temp').readline()
        return float(res.replace("temp=","").replace("'C\n",""))

    def format_time(self, d):
        if isinstance(d, (int, float)):
            return datetime.datetime.fromtimestamp(d).strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(d, datetime.datetime):
            return d.strftime('%Y-%m-%d %H:%M')

    def mem(self, human=True):
        memory_ps = psutil.virtual_memory()
        memory = dict()
        for name in memory_ps._fields:
            value = getattr(memory_ps, name)
            if name != 'percent':
                value = self.bytes2human(value) if human else value
            memory[name] = value

        swap_ps = psutil.swap_memory()
        swap = dict()
        for name in swap_ps._fields:
            value = getattr(swap_ps, name)
            if name != 'percent':
                value = self.bytes2human(value)
            swap[name] = value

        return {
            'memory': memory,
            'swap': swap
        }


    def who(self):
        users = psutil.users()

        return [{
            'name': user.name,
            'terminal': user.terminal or '-',
            'logined': self.format_time(user.started),
            'host': user.host,
        } for user in users]

    def get_public_ip(self):
        url = "http://www.telize.com/ip"
        try:
            ip = urllib2.urlopen(url).read().strip()
        except:
            ip = None

        return ip


    def boot_time(self):
        t = psutil.boot_time()

        n = time.time()

        d = datetime.timedelta(seconds=(n-t))
        days = d.days
        hours = d.seconds / 60 / 60 % 60
        minutes = d.seconds / 60 % 60
        seconds = d.seconds % 60

        return {
            'boot_time': self.format_time(t),
            'now': self.format_time(n),
            'hostname': socket.gethostname(),
            'ip': self.get_public_ip(),
            'temp': {
                'cpu': self.get_CPU_temp(),
                'gpu': self.get_GPU_temp()
            },
            'up': {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
            }
        }

    def cpu(self):
        cpu_ps = psutil.cpu_percent()
        return {
            'percent': cpu_ps,
            'load_average': os.getloadavg()
        }

    def disk_usage(self, human=True):
        parts = list()
        for part in psutil.disk_partitions(all=False):
            usage = psutil.disk_usage(part.mountpoint)
            parts.append(dict(
                device=part.device,
                total=self.bytes2human(usage.total) if human else usage.total,
                used=self.bytes2human(usage.used) if human else usage.used,
                free=self.bytes2human(usage.free) if human else usage.free,
                percent=int(usage.percent),
                fstype=part.fstype,
                mountpoint=part.mountpoint,
            ))
        return parts


    def ifconfig(self):
        pass


    def get_disk_io(self, human=True):
        read_per_sec = (self._after_disk_io.read_bytes - self._before_disk_io.read_bytes) / self._interval
        write_per_sec = (self._after_disk_io.write_bytes - self._before_disk_io.write_bytes) / self._interval
        total = (read_per_sec + write_per_sec)

        return {
            'read': (self.bytes2human(read_per_sec) if human else read_per_sec),
            'write': (self.bytes2human(write_per_sec) if human else write_per_sec),
            'total': (self.bytes2human(total) if human else total)
        }

    def get_disk_io_perdisk(self, human=True):
        disks = list()
        for name in self._after_disk_io_perdisk:
            read_per_sec = (self._after_disk_io_perdisk[name].read_bytes - self._before_disk_io_perdisk[name].read_bytes) / self._interval
            write_per_sec = (self._after_disk_io_perdisk[name].write_bytes - self._before_disk_io_perdisk[name].write_bytes) / self._interval
            total = (read_per_sec + write_per_sec)

            disks.append(dict(
                name=name,
                read=(self.bytes2human(read_per_sec) if human else read_per_sec),
                write=(self.bytes2human(write_per_sec) if human else write_per_sec),
                total=self.bytes2human(total) if human else total,
            ))
        return disks


    def _save_proces_before(self):
        for p in self._procs[:]:
            try:
                p._before = p.io_counters()
            except psutil.Error:
                self._procs.remove(p)
                continue

    def _save_proces_after(self):
        for p in self._procs[:]:
            try:
                p._after = p.io_counters()
                p._cmdline = ' '.join(p.cmdline())
                if not p._cmdline:
                    p._cmdline = p.name()
                p._username = p.username()
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                self._procs.remove(p)


    def get_net_info(self, human=True):
        net_io = {
            'total': {
                'bytes': {
                    'sent': self.bytes2human(self._net['total_after'].bytes_sent) if human else self._net['total_after'].bytes_sent,
                    'recv': self.bytes2human(self._net['total_after'].bytes_recv) if human else self._net['total_after'].bytes_recv,
                }, 'packets': {
                    'sent': self._net['total_after'].packets_sent,
                    'recv': self._net['total_after'].packets_recv,
                }
            }
        }
        bytes_sent_per_sec = (self._net['total_after'].bytes_sent - self._net['total_before'].bytes_sent) / self._interval
        bytes_recv_per_sec = (self._net['total_after'].bytes_recv - self._net['total_before'].bytes_recv) / self._interval

        if human:
            bytes_recv_per_sec = self.bytes2human(bytes_recv_per_sec)
            bytes_sent_per_sec = self.bytes2human(bytes_sent_per_sec)

        packets_sent_per_sec = (self._net['total_after'].packets_sent - self._net['total_before'].packets_sent) / self._interval
        packets_recv_per_sec = (self._net['total_after'].packets_recv - self._net['total_before'].packets_recv) / self._interval

        net_io['total']['bytes']['per_sec'] = {
            'sent': bytes_sent_per_sec,
            'recv': bytes_recv_per_sec
        }
        net_io['total']['packets']['per_sec'] = {
            'sent': packets_sent_per_sec,
            'recv': packets_recv_per_sec
        }

        pernic = list()

        for k, v in self._net['pernic_after'].items():
            t = {
                'name': k,
                'bytes': {
                    'sent': self.bytes2human(v.bytes_sent) if human else v.bytes_sent,
                    'recv': self.bytes2human(v.bytes_recv) if human else v.bytes_recv,
                }, 'packets': {
                    'sent': v.packets_sent,
                    'recv': v.packets_recv,
                }
            }
            bytes_sent_per_sec = (v.bytes_sent - self._net['pernic_before'][k].bytes_sent) / self._interval
            bytes_recv_per_sec = (v.bytes_recv - self._net['pernic_before'][k].bytes_recv) / self._interval

            if human:
                bytes_recv_per_sec = self.bytes2human(bytes_recv_per_sec)
                bytes_sent_per_sec = self.bytes2human(bytes_sent_per_sec)

            packets_sent_per_sec = (v.packets_sent - self._net['pernic_before'][k].packets_sent) / self._interval
            packets_recv_per_sec = (v.packets_recv - self._net['pernic_before'][k].packets_recv) / self._interval
            t['bytes']['per_sec'] = {
                'sent': bytes_sent_per_sec,
                'recv': bytes_recv_per_sec
            }
            t['packets']['per_sec'] = {
                'sent': packets_sent_per_sec,
                'recv': packets_recv_per_sec
            }
            addrs = netifaces.ifaddresses(k)
            t['addrs'] = {
                'ipv4': addrs.get(netifaces.AF_INET, None),
                'ipv6': addrs.get(netifaces.AF_INET6, None)
            }
            pernic.append(t)


        net_io['pernic'] = pernic

        return net_io


    def get_net_connections(self):
        AD = "-"
        AF_INET6 = getattr(socket, 'AF_INET6', object())
        proto_map = {
            (AF_INET, SOCK_STREAM): 'tcp',
            (AF_INET6, SOCK_STREAM): 'tcp6',
            (AF_INET, SOCK_DGRAM): 'udp',
            (AF_INET6, SOCK_DGRAM): 'udp6',
        }
        proc_names = {}
        for p in psutil.process_iter():
            try:
                proc_names[p.pid] = p.name()
            except psutil.Error:
                pass

        rv = list()
        for c in psutil.net_connections(kind='inet'):
            laddr = "%s:%s" % (c.laddr)
            raddr = ""
            if c.raddr:
                raddr = "%s:%s" % (c.raddr)

            temp = {
                'proto': proto_map[(c.family, c.type)],
                'local': laddr,
                'remote': raddr or AD,
                'status': c.status,
                'pid': c.pid or AD,
                'program': proc_names.get(c.pid, '?')[:15]
            }
            rv.append(temp)

        return rv


    def get_processes(self):
        processes = list()
        for proc in psutil.process_iter():
            try:
                processes.append(proc.as_dict())
            except psutil.NoSuchProcess:
                pass

        return processes


    def run(self):
        while True:
            data = dict(
                mem=self.mem(False),
                users=self.who(),
                time=self.boot_time(),
                cpu=self.cpu(),
                disk={
                    'usage': self.disk_usage(False),
                }
            )

            self._before_disk_io = psutil.disk_io_counters()
            self._before_disk_io_perdisk = psutil.disk_io_counters(True)
            self._procs = [p for p in psutil.process_iter()]
            self._net['total_before'] = psutil.net_io_counters()
            self._net['pernic_before'] = psutil.net_io_counters(True)

            sleep(self._interval)

            self._after_disk_io = psutil.disk_io_counters()
            self._after_disk_io_perdisk = psutil.disk_io_counters(True)
            self._net['total_after'] = psutil.net_io_counters()
            self._net['pernic_after'] = psutil.net_io_counters(True)

            data['disk']['io'] = self.get_disk_io(False)
            data['disk']['perdisk_io'] = self.get_disk_io_perdisk(False)
            data['net'] = self.get_net_info(False)
            data['net']['connections'] = self.get_net_connections()
            data['processes'] = self.get_processes()
            #socketio.emit('event', data)
            return data

    def stop(self):
        self.event.set()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ssss/<int:a>')
def sssss(a):
    s = StautsInfo(int(a))
    return jsonify(s.run())


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
