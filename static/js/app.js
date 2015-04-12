var app = angular.module('raspcat', ['ui.bootstrap', 'highcharts-ng', 'angularMoment']);


app.constant('angularMomentConfig', {
    preprocess: 'unix'
});


app.run(function($rootScope, $http, $timeout) {
    $rootScope.indexTpl = "/static/tpl/index.html";
});


app.filter('progressbarType', function() {
    return function(input) {
        if (input >= 90) {
            return 'danger';
        } else if (input >= 60) {
            return 'warning';
        } else if (input >= 40) {
            return 'info';
        } else {
            return 'success';
        }
    };
});


app.filter('bytes2human', function() {
    return function(size) {
        var sizes = [' Byte', ' KiB', ' MiB', ' GiB', ' TiB', ' PiB', ' EiB', ' ZiB', ' YiB'];
        for (var i = 1; i < sizes.length; i++)
        {
            if (size < Math.pow(1024, i)) return (Math.round((size/Math.pow(1024, i-1))*100)/100) + sizes[i-1];
        }
        return size;
    };
});

app.filter('seconds2human', function() {
    return function(value) {
        var days = Math.floor(value / 60 / 60 / 24);
        var hours = Math.floor(value / 60 / 60 % 24);
        var minutes = Math.floor(value / 60 % 60);
        var seconds = Math.floor(value % 60);
        var str = '';
        if (days) {
            str += days + ' d';
        }
        if (hours) {
            str += ' ' + hours + ' h';
        }
        if (minutes) {
            str += ' ' + minutes + ' m';
        }
        if (seconds) {
            str += ' ' + seconds + ' s';
        }

        return str;
    };
});

app.filter('cutfloat', function () {
    return function (value) {
        return value.toFixed(2);
    }
});

app.controller('mainController', function($scope, $timeout) {
    $scope.isSystemCollapsed = false;
    $scope.tpl = {
        path: "/static/tpl/disk.html",
        title: 'Disk'
    };
    $scope.isFull = false;
    $scope.switchFull = function() {
        //$scope.isFull = !$scope.isFull;

        $timeout(function () { // delay to reflow highchart
            $scope.$broadcast('highchartsng.reflow');
        }, 100);
    }
});

app.controller('systemController', function($scope, $http, $timeout) {
    var interval = 1;
    (function run() {
        $http.get('/api/system')
        .success(function(data) {
            if (data.status) {
                $scope.system = data.data;
                $timeout(run, interval * 1000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());

});

app.controller('diskController', function($scope, $http, $timeout, $filter) {
    var interval = 1;
    $scope.disk_all_usage = '×';
    $scope.diskTotalIOChartConfig = {
        options: {
            global: {
                useUTC: false
            },
            chart: {
                useUTC: false,
                type: 'spline'
            },
            tooltip: {
                style: {
                    padding: 10,
                    fontWeight: 'bold'
                },
                formatter: function() {
                    var text = $filter('bytes2human')(this.y);
                    text += '/s';
                    return text;
                }
            }
        },
        series: [{
            name: 'total/s',
            data: []
        }, {
            name: 'write/s',
            data: []
        }, {
            name: 'read/s',
            data: []
        }],
        title: {
            text: 'Disk Total I/O'
        },
        yAxis: {
            min: 0,
            title: {
                text: ''
            }
        },
        xAxis: {
            type: 'datetime',
            title: {
                text: 'time'
            }
        },
        loading: true
    };
    $scope.showUsagePercent = function(device, percent) {
        $scope.diskPercent = {
            device: device,
            percent: percent
        };
    };
    $scope.hideUsagePercent = function(device, percent) {
        $scope.diskPercent = undefined;
    };
    (function run() {
        $http.get('/api/disk/usage?all_disk=' + $scope.disk_all_usage)
        .success(function(data) {
            if (data.status) {
                $scope.disks = data.data;
                $timeout(run, interval * 1000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());

    (function run() {
        $http.get('/api/disk/per/io')
        .success(function(data) {
            if (data.status) {
                $scope.disks_io = data.data;
                $timeout(run, interval * 1000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());

    (function run() {
        $http.get('/api/disk/io')
        .success(function(data) {
            if (data.status) {
                $scope.disk_total_io = data.data;
                $scope.diskTotalIOChartConfig.loading = false;

                var seriesArray = $scope.diskTotalIOChartConfig.series;
                if (seriesArray[0].data.length < 6) {
                    seriesArray[0].data.push({
                        x: Date.parse(Date()),
                        y: data.data.total
                    });
                    seriesArray[1].data.push({
                        x: Date.parse(Date()),
                        y: data.data.write
                    });
                    seriesArray[2].data.push({
                        x: Date.parse(Date()),
                        y: data.data.read
                    });
                } else {
                    seriesArray[0].data.splice(0, 1);
                    seriesArray[1].data.splice(0, 1);
                    seriesArray[2].data.splice(0, 1);
                }

                $timeout(run, interval * 1000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $scope.diskTotalIOChartConfig.loading = true;
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $scope.diskTotalIOChartConfig.loading = true;
            $timeout(run, interval * 1000);
        });
    }());
});


app.controller('netController', function($scope, $http, $timeout, $filter){
    var interval = 5;

    (function run() {
        $http.get('/api/net/nic')
        .success(function(data) {
            if (data.status) {
                // console.info(data.data);
                $scope.netNic = data.data;
                $timeout(run, 10000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());
    $scope.netTotalBytesIOChartConfig = {
        options: {
            global: {
                useUTC: false
            },
            chart: {
                useUTC: false,
                type: 'spline'
            },
            tooltip: {
                style: {
                    padding: 10,
                    fontWeight: 'bold'
                }
            }
        },
        series: [{
            name: 'recv/s',
            data: []
        }, {
            name: 'sent/s',
            data: []
        }],
        title: {
            text: 'Bytes I/O'
        },
        yAxis: {
            min: 0,
            title: {
                text: ''
            }
        },
        xAxis: {
            type: 'datetime',
            title: {
                text: 'time'
            }
        },
        loading: true
    };
    $scope.netTotalPackageIOChartConfig = angular.copy($scope.netTotalBytesIOChartConfig);
    $scope.netTotalPackageIOChartConfig.title.text = "Package I/O";
    $scope.netTotalBytesIOChartConfig.options.tooltip.formatter = function() {
        var text = $filter('bytes2human')(this.y);
        text += '/s';
        return text;
    };
    $scope.netTotalPackageIOChartConfig.options.tooltip.formatter = function() {
        return this.y;
    };
    (function run() {
        $http.get('/api/net/io')
        .success(function(data) {
            if (data.status) {
                // console.info(data.data);
                $scope.netTotalIO = data.data;

                $scope.netTotalBytesIOChartConfig.loading = false;
                $scope.netTotalPackageIOChartConfig.loading = false;

                var bytesSeriesArray = $scope.netTotalBytesIOChartConfig.series;
                if (bytesSeriesArray[0].data.length < 4) {
                    bytesSeriesArray[0].data.push({
                        x: Date.parse(Date()),
                        y: data.data.bytes_recv
                    });
                    bytesSeriesArray[1].data.push({
                        x: Date.parse(Date()),
                        y: data.data.bytes_sent
                    });
                } else {
                    bytesSeriesArray[0].data.splice(0, 1);
                    bytesSeriesArray[1].data.splice(0, 1);
                }

                var packageSeriesArray = $scope.netTotalPackageIOChartConfig.series;
                if (packageSeriesArray[0].data.length <= 4) {
                    packageSeriesArray[0].data.push({
                        x: Date.parse(Date()),
                        y: data.data.package_recv
                    });
                    packageSeriesArray[1].data.push({
                        x: Date.parse(Date()),
                        y: data.data.package_sent
                    });
                } else {
                    packageSeriesArray[0].data.splice(0, 1);
                    packageSeriesArray[1].data.splice(0, 1);
                }

                $timeout(run, 1000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());

    (function run() {
        $http.get('/api/net/connections')
        .success(function(data) {
            if (data.status) {
                // console.info(data.data);
                $scope.connections = data.data;
                $scope.proto = [];
                $scope.status = [];
                var local = {};
                var remote = {};
                var re = /(\d+\.\d+\.\d+\.\d+):(\d+)/;
                angular.forEach(data.data, function(value, key) {
                    if ($scope.proto.indexOf(value.proto) == -1) {
                        $scope.proto.push(value.proto);
                    }
                    if ($scope.status.indexOf(value.status) == -1) {
                        $scope.status.push(value.status);
                    }
                    var rv = re.exec(value.local);
                    if (rv) {
                        var item = {
                            ip: rv[1],
                            port: rv[2]
                        };
                        if (item.ip in local) {
                            if (local[item.ip].indexOf(item.port) == -1) {
                                local[item.ip].push(item.port);
                            }
                        } else {
                            local[item.ip] = [];
                        }
                    }
                });
                $scope.local = [];
                angular.forEach(local, function(value, key) {
                    this.push({
                        ip: key,
                        port: "*"
                    });
                    for (var i = 0; i < value.length; i++) {
                        this.push({
                            ip: key,
                            port: value[i]
                        });
                    }
                }, $scope.local);
                // remote
                angular.forEach(data.data, function(value, key) {
                    if ($scope.proto.indexOf(value.proto) == -1) {
                        $scope.proto.push(value.proto);
                    }
                    if ($scope.status.indexOf(value.status) == -1) {
                        $scope.status.push(value.status);
                    }
                    var rv = re.exec(value.remote);
                    if (rv) {
                        var item = {
                            ip: rv[1],
                            port: rv[2]
                        };
                        if (item.ip in remote) {
                            if (remote[item.ip].indexOf(item.port) == -1) {
                                remote[item.ip].push(item.port);
                            }
                        } else {
                            remote[item.ip] = [];
                        }
                    }
                });
                $scope.remote = [];
                angular.forEach(remote, function(value, key) {
                    this.push({
                        ip: key,
                        port: "*"
                    });
                    for (var i = 0; i < value.length; i++) {
                        this.push({
                            ip: key,
                            port: value[i]
                        });
                    }
                }, $scope.remote);
                $timeout(run, 1000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());
});

app.controller('processesController', function ($scope, $http, $timeout) {
    (function run() {
        $http.get('/api/processes')
        .success(function(data) {
            if (data.status) {
                //console.info(data.data);
                $scope.processes = data.data;
                $timeout(run, 10000);
            } else {
                interval *= interval + 1;
                console.error('retry after ' + interval + ' seconds.');
                $timeout(run, interval * 1000);
            }
        })
        .error(function(data, status, headers, config) {
            interval *= interval + 1;
            console.error('retry after ' + interval + ' seconds.');
            $timeout(run, interval * 1000);
        });
    }());
});