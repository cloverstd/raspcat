#!/usr/bin/env python
# encoding: utf-8

from flask import Flask, render_template, jsonify, request
from gevent.wsgi import WSGIServer
from gevent import sleep
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM
import socket
import time
import psutil
import urllib2
import os
import netifaces

app = Flask(__name__)

app.config.from_object('config')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/mem')
def api_mem():
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message
        })

    return jsonify({
        'status': True,
        'data': {
            'mem': mem._asdict(),
            'swap': swap._asdict(),
        }
    })


@app.route('/api/disk/usage')
def api_disk_usage():
    try:
        all_disk = request.args.get('all_disk')
        if all_disk == '✓':
            all_disk = True
        else:
            all_disk = False
        parts = list()
        for part in psutil.disk_partitions(all=all_disk):
            usage = psutil.disk_usage(part.mountpoint)._asdict()
            part = part._asdict()
            usage.update(part)
            parts.append(usage)

        return jsonify({
            'status': True,
            'data': parts
        })
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message,
        })



@app.route('/api/disk/io')
@app.route('/api/disk/io/<int:interval>')
def api_disk_io(interval=1):
    try:
        before_disk_io = psutil.disk_io_counters()
        sleep(interval)
        after_disk_io = psutil.disk_io_counters()
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message,
        })
    else:
        read_per = after_disk_io.read_bytes - before_disk_io.read_bytes
        write_per = after_disk_io.write_bytes - before_disk_io.write_bytes

        total = (read_per + write_per)

        return jsonify({
            'status': True,
            'data': {
                'read': read_per / interval,
                'write': write_per / interval,
                'total': total / interval
            }
        })


@app.route('/api/disk/per/io')
@app.route('/api/disk/per/io/<int:interval>')
def api_per_disk_io(interval=1):
    try:
        before_per_disk_io = psutil.disk_io_counters(perdisk=True)
        sleep(interval)
        after_per_disk_io = psutil.disk_io_counters(perdisk=True)

        disks = list()
        for name in after_per_disk_io:
            disk_after = after_per_disk_io[name]
            disk_before = before_per_disk_io[name]
            read_per = disk_after.read_bytes - disk_before.read_bytes
            write_per = disk_after.write_bytes - disk_before.write_bytes
            total = read_per + write_per

            disks.append({
                'name': name,
                'read': read_per / interval,
                'write': write_per / interval,
                'total': total / interval
            })

        return jsonify({
            'status': True,
            'data': disks
        })
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message
        })

@app.route('/api/net/ip')
def api_net_ip():
    url = "http://www.telize.com/ip"
    try:
        ip = urllib2.urlopen(url).read().strip()
    except:
        ip = None

    return jsonify({
        'status': True,
        'data': ip
    })


@app.route('/api/system')
def api_system():
    try:
        res = os.popen('/opt/vc/bin/vcgencmd measure_temp').readline()
        gpu_temp = float(res.replace("temp=","").replace("'C\n",""))

        cpu_temp = None

        with open('/sys/class/thermal/thermal_zone0/temp') as fp:
            cpu_temp = fp.read()
            cpu_temp = float(cpu_temp) / 1000

        users = [{
                'name': user.name,
                'terminal': user.terminal or '-',
                'logined': user.started,
                'host': user.host,
            } for user in psutil.users()]

        return jsonify({
            'status': True,
            'data': {
                'users': users,
                'boot_time': psutil.boot_time(),
                'now': time.time(),
                'hostname': socket.gethostname(),
                'temp': {
                    'GPU': gpu_temp,
                    'CPU': cpu_temp,
                }
            }
        })
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message,
        })


@app.route('/api/cpu')
def get_cpu_info():
    try:
        return jsonify({
            'status': True,
            'data': {
                'percent': psutil.cpu_percent(),
                'load_average': os.getloadavg(),
            }
        })
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message,
        })


@app.route('/api/processes')
def get_processes():
    try:
        processes = list()
        for proc in psutil.process_iter():
            try:
                processes.append(proc.as_dict())
            except psutil.NoSuchProcess:
                pass

        return jsonify({
            'status': True,
            'data': processes,
        })
    except Exception as e:
        print e
        return jsonify({
            'status': False,
            'err': e.message,
        })


@app.route('/api/net/nic')
def api_net_nic():
    try:
        ifaddresses = list()
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            ip = addrs.get(netifaces.AF_INET)

            ifaddresses.append({
                interface: ip[0] if ip else None,
            })

        return jsonify({
            'status': True,
            'data': ifaddresses,
        })
    except Exception as e:
        return jsonify({
            'status': False,
            'err': e.message,
        })


@app.route('/api/net/io')
@app.route('/api/net/io/<int:interval>')
def api_net_io(interval=1):
    net_io_before = psutil.net_io_counters()
    sleep(interval)
    net_io_after = psutil.net_io_counters()

    bytes_sent_per = net_io_after.bytes_sent - net_io_before.bytes_sent
    bytes_recv_per = net_io_after.bytes_recv - net_io_before.bytes_recv

    package_sent_per = net_io_after.packets_sent - net_io_before.packets_sent
    package_recv_per = net_io_after.packets_recv - net_io_before.packets_recv


    return jsonify({
        'status': True,
        'data': {
            'bytes_recv': bytes_recv_per / interval,
            'bytes_sent': bytes_sent_per / interval,
            'package_sent': int(package_sent_per / interval),
            'package_recv': int(package_recv_per / interval),
        }
    })



@app.route('/api/net/per/io')
@app.route('/api/net/per/io/<int:interval>')
def api_net_per_io(interval=1):
    net_io_before = psutil.net_io_counters(pernic=True)
    sleep(interval)
    net_io_after = psutil.net_io_counters(pernic=True)

    nics = list()

    for nic_name in net_io_after:
        nic_after = net_io_after[nic_name]
        nic_before = net_io_before[nic_name]

        bytes_sent_per = nic_after.bytes_sent - nic_before.bytes_sent
        bytes_recv_per = nic_after.bytes_recv - nic_before.bytes_recv

        package_sent_per = nic_after.packets_sent - nic_before.packets_sent
        package_recv_per = nic_after.packets_recv - nic_before.packets_recv

        nics.append({
            nic_name: {
                'bytes_recv': bytes_recv_per / interval,
                'bytes_sent': bytes_sent_per / interval,
                'package_sent': int(package_sent_per / interval),
                'package_recv': int(package_recv_per / interval),
            }
        })

    return jsonify({
        'status': True,
        'data': nics
    })


@app.route('/api/net/connections')
def api_net_connections():
    connections = list()

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
        connections.append(temp)

    return jsonify({
        'status': True,
        'data': connections,
    })


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
