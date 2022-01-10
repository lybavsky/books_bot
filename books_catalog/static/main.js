document.addEventListener("DOMContentLoaded", ready);

function ready(e) {
    update_scan_status()
    setInterval(update_scan_status, 5000)
}

function update_scan_status() {
    var opts = {
        method: 'GET',
        headers: {}
    };
    fetch('/scan/status', opts).then(function (response) {
        return response.json();
    })
        .then(function (body) {
            var res = ""
            if (body.status == -1) {
                btn = "<button onclick='start_scan()'>Start</button>"
                res = body.processed + " books" + btn
            } else if (body.status == -2) {
                btn = "<button onclick='start_scan()'>Start</button>"
                res = body.processed + " books, error: " + body.erro + btn
            } else {
                btn = "<button onclick='stop_scan()'>Stop</button>"
                res = "Scanning: " + body.processed + "/" + body.books_all + btn
            }
            document.getElementById("scan_status_cont").innerHTML = res

        });
}

function start_scan() {
    var opts = {
        method: 'GET',
        headers: {}
    };
    fetch('/scan/start', opts).then(function (response) {
        return response.json();
    })
        .then(function (body) {
            update_scan_status()
        });
}

function stop_scan() {
    var opts = {
        method: 'GET',
        headers: {}
    };
    fetch('/scan/stop', opts).then(function (response) {
        return response.json();
    })
        .then(function (body) {
            update_scan_status()
        });
}