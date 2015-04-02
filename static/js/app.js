var app = angular.module('raspcat', ['ui.bootstrap', 'highcharts-ng']);

app.run(function($rootScope) {
    $rootScope.indexTpl = "/static/tpl/index.html";
    $rootScope.memTpl = "/static/tpl/mem.html";
});

app.factory('status', function($rootScope, $http, $timeout) {
    return function() {
        var timeout = 5000;
        function run() {
            $http.get('/ssss/1')
            .success(function(data) {
                $rootScope.$broadcast('status', data);
                $timeout(function() { run(); }, 1);
            })
            .error(function(err) {
                console.error(err);
                timeout += 1000;
                $timeout(function() { run(); }, timeout);
            });
        }
        run();
    }();
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
        var sizes = [' B', ' K', ' M', ' G', ' T', ' P', ' E', ' Z', ' Y'];
        for (var i = 1; i < sizes.length; i++)
        {
            if (size < Math.pow(1024, i)) return (Math.round((size/Math.pow(1024, i-1))*100)/100) + sizes[i-1];
        }
        return size;
    };
});



app.controller('memController', function($scope, $http, status) {
    $scope.$on('status', function(ev, data) {
        $scope.mem = data.mem;
    });
});

app.controller('statusController', function($scope, $http, status) {
    $scope.$on('status', function(ev, data) {
        $scope.users = data.users;
        $scope.time = data.time;
        $http.jsonp('http://www.telize.com/geoip/' + data.time.ip + '?callback=JSON_CALLBACK')
        .success(function(data) {
            $scope.ip_tooltips = data.country;
            if (data.region) {
                $scope.ip_tooltips += '/' + data.region;
            }
            if (data.city) {
                $scope.ip_tooltips += '/' + data.city;
            }
        });
    });
});

app.controller('diskController', function($scope, $http, status, $filter) {
    $scope.chartConfig = {
        options: {
            chart: {
                type: 'spline'
            }
        },
        plotOptions: {
            series: {
                stacking: ""
            }
        },
        title: {
            text: 'I/O'
        },
        credits: {
            enabled: true
        },
        loading: true,
        series: [
            {
                name: 'total',
                data: [],
                tooltip: {
                    headerFormat: 'header',
                    footerFormat: 'footer',
                    pointFormatter: function () {
                        return 'The value for <b>' + this.x +
                        '</b> is <b>' + this.y + '</b>';
                    }
                }
            }, {
                name: 'total read',
                data: []
            }, {
                name: 'total write',
                data: []
            }
        ],
        xAxis: {
            type: 'datetime',
            title: {
                text: 'Time'
            }
        },
        yAxis: {
            title: {
                text: 'value'
            },
            min: 0
        }
    };
    function render(name, value, index, date) {
        $scope.chartConfig.series[index].name = name;
        if ($scope.chartConfig.series[index].data.length === 6) {
            $scope.chartConfig.series[index].data.splice(0, 1);
        }
        $scope.chartConfig.series[index].data.push({
            x: Date.parse(date),
            y: value
        });
    }
    $scope.$on('status', function(ev, data) {
        $scope.chartConfig.loading = false;
        $scope.disk = data.disk;
        render('total', data.disk.io.total, 0, data.time.now);
        render('total read', data.disk.io.read, 1, data.time.now);
        render('total write', data.disk.io.write, 2, data.time.now);
        

    });
});


app.controller('cpuController', function($scope, $http, status) {
    $scope.percentChartConfig = {
        options: {
            chart: {
                type: 'spline'
            }
        },
        title: {
            text: 'CPU Percent'
        },
        credits: {
            enabled: true
        },
        loading: true,
        series: [{
            name: 'CPU',
            data: [],
            dataLabels: {
                enabled: true,
                formatter: function () {
                    return this.y + '%';
                }
            },
            tooltip: {
                enabled: true,
                pointFormat: '{point.y}%'
            }
        }],
        xAxis: {
            type: 'datetime',
            title: {
                text: 'Time'
            }
        },
        yAxis: {
            title: {
                text: 'value'
            },
            min: 0
        }
    };
    $scope.loadChartConfig = {
        options: {
            chart: {
                type: 'spline'
            }
        },
        title: {
            text: 'Load Average'
        },
        credits: {
            enabled: true
        },
        loading: true,
        series: [{
            name: '1m',
            data: [],
            dataLabels: {
                enabled: false
            }
        }, {
            name: '5m',
            data: [],
            dataLabels: {
                enabled: false
            }

        }, {
            name: '15m',
            data: [],
            dataLabels: {
                enabled: false
            }

        }],
        xAxis: {
            type: 'datetime',
            title: {
                text: 'Time'
            }
        },
        yAxis: {
            title: {
                text: 'value'
            },
            min: 0,
            formatter: function() {
                return this.value + '/s';
            }
        }
    };
    $scope.$on('status', function(ev, data) {
        $scope.percentChartConfig.loading = false;
        $scope.loadChartConfig.loading = false;
        $scope.cpu = data.cpu;
        if ($scope.percentChartConfig.series[0].data.length === 6) {
            $scope.percentChartConfig.series[0].data.splice(0, 1);
        }
        $scope.percentChartConfig.series[0].data.push({
            x: Date.parse(data.time.now),
            y: data.cpu.percent
        });

        if ($scope.loadChartConfig.series[0].data.length === 6) {
            $scope.loadChartConfig.series[0].data.splice(0, 1);
            $scope.loadChartConfig.series[1].data.splice(0, 1);
            $scope.loadChartConfig.series[2].data.splice(0, 1);
        }

        $scope.loadChartConfig.series[0].data.push({
            x: Date.parse(data.time.now),
            y: data.cpu.load_average[0]
        });
        $scope.loadChartConfig.series[1].data.push({
            x: Date.parse(data.time.now),
            y: data.cpu.load_average[1]
        });
        $scope.loadChartConfig.series[2].data.push({
            x: Date.parse(data.time.now),
            y: data.cpu.load_average[2]
        });

    });
});


app.controller('netController', function($scope, $http, status) {
    $scope.$on('status', function(ev, data) {
        $scope.net = data.net;
    });
});