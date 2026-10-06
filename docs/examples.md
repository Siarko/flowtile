# Examples

Five self-contained examples, each building on the previous. Together they cover most of the app's features. Adapt paths and script names to your own deployment.

---

## 1. Clock and uptime

The simplest useful screen: a large clock on top, uptime below.

```sh
# scripts/uptime.sh
#!/bin/sh
awk '{
    s = int($1)
    d = int(s/86400); s = s % 86400
    h = int(s/3600);  s = s % 3600
    m = int(s/60)
    printf "%dd %02d:%02d\n", d, h, m
}' /proc/uptime
```

```yaml
# sources.yaml
sources:
  time:
    script: ["date", "+%H:%M:%S"]
    exec_mode: repeat
    refresh: 1
  uptime:
    script: ["/bin/sh", "!cwd scripts/uptime.sh"]
    exec_mode: repeat
    refresh: 5
```

```yaml
# screens.yaml
screens:
  home:
    label: Home
    component:
      home.root:
        direction: column
        children:
          home.time:
            size: 70
            align: center
            align_v: middle
            font_size: 20
            data:
              source: time
          home.uptime:
            align: center
            align_v: middle
            color_bg: 50
            data:
              source: uptime
              output_format: "up {input}"
```

```yaml
# navigation.yaml
navigation:
  main:
    root: true
    default: home
    direction: row
    elements:
      - home
```

---

## 2. CPU and RAM with progress bars

Two gauges side by side. Each has a label and a progress bar driven by a script. Component inheritance keeps shared styling in one place.

The scripts output:
- `cpu_info` → `75%`
- `ram_info` → `874M / 1024M`

```sh
# scripts/cpu_info.sh - outputs e.g. "75%"
#!/bin/sh
snapshot() { awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5}' /proc/stat; }
prev=$(snapshot); sleep 1; curr=$(snapshot)
awk -v p="$prev" -v c="$curr" 'BEGIN {
    split(p, a); split(c, b)
    diff_total = b[1] - a[1]
    diff_idle  = b[2] - a[2]
    if (diff_total > 0)
        printf "%d%%\n", 100 * (diff_total - diff_idle) / diff_total
    else
        print "0%"
}'
```

```sh
# scripts/ram_info.sh - outputs e.g. "874M / 1024M"
#!/bin/sh
awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} END {
    printf "%dM / %dM\n", (t-a)/1024, t/1024
}' /proc/meminfo
```

```yaml
# sources.yaml
sources:
  cpu_info:
    script: ["/bin/sh", "!cwd scripts/cpu_info.sh"]
    exec_mode: repeat
    refresh: 3
  ram_info:
    script: ["/bin/sh", "!cwd scripts/ram_info.sh"]
    exec_mode: repeat
    refresh: 3
```

```yaml
# components.yaml
components:
  gauge.label:           # reusable label style
    align: center
    align_v: middle
    color: 0
    color_bg: 255
    font_size: 8

  gauge.bar:             # reusable progress bar style
    padding: 2
    border: 1
    border_color: rgb(80,80,80)
    align: center
    align_v: middle
    content_render:
      type: progressbar

  system.monitor:
    direction: row
    children:
      sys.cpu:
        direction: column
        size: 50
        children:
          sys.cpu.label:
            parent: gauge.label
            size: 14px
            data:
              source: !type:text CPU
          sys.cpu.bar:
            parent: gauge.bar
            data:
              source: cpu_info
              source_format: "{value:d}%"
      sys.ram:
        direction: column
        children:
          sys.ram.label:
            parent: gauge.label
            size: 14px
            data:
              source: !type:text RAM
          sys.ram.bar:
            parent: gauge.bar
            data:
              source: ram_info
              source_format: "{value:d}M / {max:d}M"
              # "max" variable overrides the progressbar's static max per line
```

```yaml
# screens.yaml
screens:
  sysmon:
    label: System
    component: system.monitor
```

---

## 3. Network traffic with scrolling charts

Two charts - download and upload - sampling continuously in the background. Labels above each chart show the current rate formatted as human-readable bytes.

The script outputs one line per refresh: `rx_bytes/tx_bytes` e.g. `204800/51200`.

```sh
# scripts/wan_traffic.sh - outputs e.g. "204800/51200" (rx_bytes/tx_bytes over 0.5s)
#!/bin/sh
IFACE=$(ip route show default | awk '/default/ { print $5; exit }')
[ -z "$IFACE" ] && exit 1

read_stat() {
    awk -v iface="$IFACE:" '$1 == iface { print $2, $10 }' /proc/net/dev
}

prev=$(read_stat); sleep 0.5; curr=$(read_stat)

rx=$(( $(echo $curr | cut -d' ' -f1) - $(echo $prev | cut -d' ' -f1) ))
tx=$(( $(echo $curr | cut -d' ' -f2) - $(echo $prev | cut -d' ' -f2) ))
echo "$rx/$tx"
```

```yaml
# sources.yaml
sources:
  wan:
    script: ["/bin/sh", "!cwd scripts/wan_traffic.sh"]
    exec_mode: repeat
    refresh: 1
```

```yaml
# config.yaml (general section)
general:
  screen_fps: 10
  transform:
    functions:
      - transform/format_bytes   # registers format_bytes(n) -> "200 KB"
```

```yaml
# screens.yaml
screens:
  home:
    label: Home
    component:
      home.root:
        direction: column
        children:
          home.labels:
            direction: row
            size: 12px
            children:
              home.rx.label:
                align: center
                data:
                  source: wan
                  source_format: "{rx:d}/{_}"
                  transform:
                    - format_bytes(rx) > rx
                  output_format: "↓ {rx}/s"
              home.tx.label:
                align: center
                data:
                  source: wan
                  source_format: "{_}/{tx:d}"
                  transform:
                    - format_bytes(tx) > tx
                  output_format: "↑ {tx}/s"
          home.charts:
            direction: row
            children:
              home.rx.chart:
                persist: true
                data:
                  source: wan
                  source_format: "{value:d}/{_}"
                content_render:
                  type: chart
                  format: "{value:d}"
                  autoscale: true
                  sample_count: 60
              home.tx.chart:
                persist: true
                data:
                  source: wan
                  source_format: "{_}/{value:d}"
                content_render:
                  type: chart
                  format: "{value:d}"
                  autoscale: true
                  sample_count: 60
```

---

## 4. Multi-screen grid navigation

Four screens arranged in a 2×2 grid: left/right moves between "home" and "network"; up/down switches between the normal view and a detail view for each column.

```yaml
# screens.yaml
screens:
  home:
    label: Home
    component:
      home.root:
        direction: column
        children:
          home.title:
            parent: gauge.label
            data:
              source: !type:text HOME
          home.uptime:
            align: center
            align_v: middle
            data:
              source: uptime

  home.detail:
    label: CPU detail
    component: system.monitor   # reuses the component from example 2

  network:
    label: Network
    component:
      net.root:
        direction: column
        children:
          net.title:
            parent: gauge.label
            data:
              source: !type:text NETWORK
          net.chart.rx:
            persist: true
            data:
              source: wan
              source_format: "{value:d}/{_}"
            content_render:
              type: chart
              format: "{value:d}"
              autoscale: true

  network.detail:
    label: WAN detail
    component:
      netdetail.root:
        direction: column
        children:
          netdetail.rx:
            data:
              source: wan
              source_format: "{rx:d}/{tx:d}"
              transform:
                - format_bytes(rx) > rx
                - format_bytes(tx) > tx
              output_format: "↓ {rx}/s  ↑ {tx}/s"
```

```yaml
# navigation.yaml
navigation:
  main:                    # left/right: home ↔ network
    root: true
    default: home
    direction: row
    wrap: true
    elements:
      - !axis left.column
      - !axis right.column

  left.column:             # up/down: home ↔ home.detail
    direction: column
    elements:
      - home
      - home.detail

  right.column:            # up/down: network ↔ network.detail
    direction: column
    elements:
      - network
      - network.detail
```

Navigation: pressing left/right moves between columns; pressing up/down within any column toggles between the overview and the detail screen for that column.

---

## 5. Client list with conditional styling

Shows connected network clients - parsed from a multi-line script output - with the count highlighted in red when it exceeds a threshold.

The script prints one line per client: `192.168.1.10 laptop`, one client per line, ending with `EOF`.

```sh
# scripts/clients.sh - prints "ip hostname" per connected client, ends with EOF
#!/bin/sh
awk '/0x2/ { ip=$1; mac=$4; printf "%s %s\n", ip, mac }' /proc/net/arp
echo EOF
```

> The script reads the ARP table for reachable hosts (`0x2` = complete entry). Replace with `ip neigh` or a DHCP lease file parse if you have hostname resolution available.

```yaml
# sources.yaml
sources:
  clients:
    script: ["/bin/sh", "!cwd scripts/clients.sh"]
    exec_mode: repeat
    refresh: 10
    eof_string: EOF
```

```yaml
# screens.yaml
screens:
  clients:
    label: Clients
    component:
      clients.root:
        direction: column
        children:
          clients.header:
            direction: row
            size: 14px
            children:
              clients.header.title:
                size: 70
                align: center
                align_v: middle
                color_bg: 50
                data:
                  source: !type:text CLIENTS
              clients.header.count:
                align: center
                align_v: middle
                color: !var clients.count.alert_color  # red when over threshold
                data:
                  source: clients
                  source_multiline: true
                  static:
                    alert_color: 255
                  transform:
                    - split(input, "\n") > lines
                    - count(lines) > n
                    - if(n > 10) 200 > alert_color    # set red
                    - if(n <= 10) 255 > alert_color   # set white
                    - n > alert_color                  # publish for !var
                  output_format: "{n}"
          clients.list:
            align_v: top
            data:
              source: clients
              source_multiline: false   # one pass per line
              transform:
                - trim(input) > line
                - split(line, " ") > parts
                - parts[1] > ip
                - parts[0] > hostname      # script prints "ip hostname"
              output_format: "{ip}  {hostname}"
```

> **Note:** `color: !var clients.count.alert_color` reads the `alert_color` variable published by the `clients.header.count` component's pipeline. The `!var component.variable` form cross-references another component's output. The header component uses `output_format: "{n}"` so the count is shown as text, while also publishing `alert_color` for the sibling to read via `!var`.

