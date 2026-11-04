(function () {
  var root = document.querySelector("[data-refresh]");
  if (!root) {
    return;
  }
  var url = root.getAttribute("data-refresh");
  var kind = root.getAttribute("data-refresh-kind");

  function cell(id, text) {
    var el = document.getElementById(id);
    if (el) {
      el.textContent = text;
    }
  }

  function applyList(data) {
    (data.servers || []).forEach(function (server) {
      cell("status-" + server.id, server.status);
      cell("cpu-" + server.id, server.cpu_text);
      cell("memory-" + server.id, server.memory_text);
      cell("seen-" + server.id, server.last_success_text);
    });
  }

  function fillRow(values) {
    var tr = document.createElement("tr");
    values.forEach(function (value) {
      var td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });
    return tr;
  }

  function applyDetail(data) {
    var server = data.server;
    if (!server) {
      return;
    }
    cell("server-status", server.status);
    cell("server-last-success", server.last_success_text);
    cell("server-cpu", server.cpu_text);
    cell("server-memory", server.memory_text);
    var message = document.getElementById("server-message");
    if (message) {
      message.textContent = server.message || "";
      message.hidden = !server.message;
    }
    var network = document.getElementById("network-rows");
    if (network) {
      network.replaceChildren();
      if (!server.network || !server.network.length) {
        var emptyNet = fillRow(["No network data."]);
        emptyNet.firstChild.colSpan = 5;
        network.appendChild(emptyNet);
      } else {
        server.network.forEach(function (iface) {
          network.appendChild(fillRow([
            iface.name,
            iface.rx_text,
            iface.tx_text,
            iface.rx_rate_text,
            iface.tx_rate_text
          ]));
        });
      }
    }
    var ports = document.getElementById("ports-rows");
    if (ports) {
      ports.replaceChildren();
      if (!server.ports || !server.ports.length) {
        var emptyPorts = fillRow(["No listening ports."]);
        emptyPorts.firstChild.colSpan = 4;
        ports.appendChild(emptyPorts);
      } else {
        server.ports.forEach(function (port) {
          ports.appendChild(fillRow([
            port.protocol,
            port.address,
            String(port.port),
            port.process_text
          ]));
        });
      }
    }
  }

  function tick() {
    fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) {
          return null;
        }
        return response.json();
      })
      .then(function (data) {
        if (!data) {
          return;
        }
        if (kind === "detail") {
          applyDetail(data);
        } else {
          applyList(data);
        }
      })
      .catch(function () {});
  }

  setInterval(tick, 15000);
})();
